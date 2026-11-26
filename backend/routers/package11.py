"""Read-only, authenticated usage inventory; never invokes AI."""
from datetime import datetime, timezone
from fastapi import Depends, HTTPException
from azure.core.exceptions import ResourceNotFoundError
from shared.user_authorization import require_authorised_user
from shared.table_storage import get_table_client
from shared.config import get_settings
from routers.remaining import router

@router.get('/package11/usage')
def usage(user=Depends(require_authorised_user)):
    try:
        table=get_table_client(get_settings().metrics_table)
        now=datetime.now(timezone.utc)
        day=now.strftime('%Y%m%d'); month=day[:6]
        rows=table.query_entities('PartitionKey eq @p',parameters={'p':user['user_id']},results_per_page=100,select=['RowKey','InputTokens','OutputTokens','DurationSeconds','ExerciseId'])
        count=inp=out=0; duration=0.0; scanned=0; truncated=False
        for row in rows:
            if scanned>=1000: truncated=True; break
            scanned+=1
            if not row['RowKey'].startswith(('expanded-','run-')): continue
            count+=1; inp+=int(row.get('InputTokens') or 0); out+=int(row.get('OutputTokens') or 0); duration+=float(row.get('DurationSeconds') or 0)
        limits=[('audio',day,5),('voice',day,3),('video-day',day,2),('video-month',month,5)]
        quotas=[]
        quota_table=get_table_client(get_settings().configuration_table)
        for kind,period,limit in limits:
            used=0
            for i in range(limit):
                try: quota_table.get_entity('package8-quota',f'{kind}-{period}-{i}'); used+=1
                except ResourceNotFoundError: pass
            quotas.append({'service':kind,'period_utc':period,'reserved_attempts':used,'limit':limit})
        return {'recorded_runs':count,'recorded_input_tokens':inp,'recorded_output_tokens':out,'recorded_duration_seconds':round(duration,2),'records_scanned':scanned,'truncated':truncated,'multimedia_quotas':quotas,'monthly_budget_aud':50,'video_allowance_aud':5,'actual_billed_cost_aud':None,'scope':'Recorded personal expanded/chat metrics only; multimedia reservations are shared. Not a complete usage ledger or billing feed. Budget values are planning targets.'}
    except Exception:
        raise HTTPException(503,'Usage inventory unavailable') from None
