"""Authenticated, read-only lab resource-group cost query (not an invoice)."""
from datetime import datetime, timezone
from threading import Lock
from time import monotonic
import httpx
from fastapi import Depends, HTTPException
from shared.auth import get_azure_credential
from shared.user_authorization import require_authorised_user
from routers.remaining import router

SUBSCRIPTION = 'a37bf3fc-3e0b-46ca-bdf7-defade9c9e93'
GROUPS = ('AI103-LAB-RG','rg-ai103-showcase','rg-ai103-persistent','rg-ai103-runtime','rg-ai103-specialised')
_lock = Lock()
_cache = None
_cached_at = 0.0

def parse_cost(payload):
    props = payload['properties']
    if props.get('nextLink'):
        raise ValueError('Unexpected paginated aggregate')
    cols = [c['name'].lower() for c in props['columns']]
    cost = next(i for i,n in enumerate(cols) if n in ('cost','pretaxcost','totalcost'))
    currency = cols.index('currency')
    totals = {}
    for row in props['rows']:
        unit = str(row[currency])
        totals[unit] = totals.get(unit, 0.0) + float(row[cost])
    return {k:round(v,4) for k,v in totals.items()}

@router.get('/package13/cost')
def cost(user=Depends(require_authorised_user)):
    global _cache, _cached_at
    with _lock:
        if _cache is not None and monotonic()-_cached_at < 900:
            return _cache
        try:
            token = get_azure_credential().get_token('https://management.azure.com/.default').token
            body = {'type':'ActualCost','timeframe':'MonthToDate','dataset':{'granularity':'None','aggregation':{'totalCost':{'name':'PreTaxCost','function':'Sum'}}}}
            groups=[]
            with httpx.Client(timeout=10, follow_redirects=False) as client:
                for group in GROUPS:
                    url=f'https://management.azure.com/subscriptions/{SUBSCRIPTION}/resourceGroups/{group}/providers/Microsoft.CostManagement/query?api-version=2023-11-01'
                    r=client.post(url,json=body,headers={'Authorization':'Bearer '+token})
                    if r.status_code==204:
                        groups.append({'group':group,'status':'no_data','totals':{}})
                    elif r.status_code==200:
                        try: groups.append({'group':group,'status':'reported','totals':parse_cost(r.json())})
                        except (ValueError,KeyError,IndexError,StopIteration,TypeError): groups.append({'group':group,'status':'unrecognised_response','totals':{}})
                    else:
                        groups.append({'group':group,'status':f'HTTP {r.status_code}','totals':{}})
            totals={}
            for group in groups:
                for currency,value in group['totals'].items(): totals[currency]=round(totals.get(currency,0)+value,4)
            _cache={'as_of_utc':datetime.now(timezone.utc).isoformat(),'groups':groups,'reported_totals':totals,'complete':all(g['status']=='reported' for g in groups),'monthly_budget_target_aud':50,'scope':'Month-to-date actual cost reported by Azure for five lab resource groups; shared resources may include other workloads. Missing groups are not zero. Billing is delayed; taxes, credits and invoice totals may differ.'}
            _cached_at=monotonic()
            return _cache
        except Exception:
            raise HTTPException(503,'Azure cost query unavailable; check Cost Management Reader access and billing support') from None
