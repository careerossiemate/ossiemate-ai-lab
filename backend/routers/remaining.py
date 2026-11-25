import json, os, base64
from time import perf_counter
from threading import BoundedSemaphore
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from shared.auth import get_azure_credential
from shared.user_authorization import require_authorised_user
from routers.expanded import reserve_service, LIMITS
from routers.final_labs import model
router=APIRouter(prefix='/api/remaining')
LIMITS.update({'search':(10,2),'cu':(5,1),'flux':(3,1)})
slots=BoundedSemaphore(1)
GUIDES={
'AG01':'Create a native agent in the Foundry project and verify project permissions.',
'AG03':'Configure an approved MCP server and verify tool discovery and invocation.',
'AG04':'Create a Foundry IQ knowledge base connected to the Search index.',
'AG06':'Publish a native agent to Teams after tenant administrator approval.',
'AG08':'Install and validate the Microsoft Agent Framework SDK against the project.',
'AG10':'Configure authenticated remote A2A agent cards and message endpoints.',
'LG03':'Deploy a supported generative audio model after pricing approval.',
'LG05':'Enable a supported Speech MCP endpoint and authenticate its tools.',
'LG06':'Validate Voice Live model availability and streaming session authentication.',
'VS03':'Confirm Sora model availability and approve video generation pricing.',
}
class Request(BaseModel):
    exercise:str=Field(max_length=4)
    prompt:str=Field(default='',max_length=2000)
    image:str=Field(default='',max_length=700000)
    mime:str=Field(default='image/png',max_length=30)

def headers(scope):
    return {'Authorization':'Bearer '+get_azure_credential().get_token(scope).token}

@router.get('/capabilities')
def capabilities(user=Depends(require_authorised_user)):
    return {'experimental':['VS02','VS08','VS04','VS05','VS06'],'local_validation':['05'],'blocked':GUIDES}

@router.post('/run')
def run(body:Request,user=Depends(require_authorised_user)):
    eid=body.exercise; uid=user['user_id']; start=perf_counter()
    if eid in GUIDES: raise HTTPException(503,GUIDES[eid])
    if eid not in ('VS02','05','VS08','VS04','VS05','VS06'): raise HTTPException(404,'Unknown exercise')
    if not slots.acquire(False): raise HTTPException(429,'Service busy')
    try:
        if eid=='VS02':
            if not body.prompt.strip(): raise HTTPException(422,'Enter an image prompt')
            reserve_service('global-image-budget','flux')
            with httpx.Client(timeout=110,headers=headers('https://cognitiveservices.azure.com/.default')) as c:
                r=c.post('https://ai103-agent-lab.services.ai.azure.com/openai/v1/images/generations',params={'api-version':'preview'},json={'model':'flux-lab','prompt':body.prompt,'n':1,'size':'1024x1024','response_format':'b64_json'})
                r.raise_for_status()
                encoded=r.json()['data'][0]['b64_json']
                raw=base64.b64decode(encoded,validate=True)
                if len(raw)>8000000: raise HTTPException(502,'Image exceeds display limit')
                mime='image/png' if raw.startswith(b'\x89PNG\r\n\x1a\n') else 'image/jpeg' if raw.startswith(b'\xff\xd8\xff') else None
                if not mime: raise HTTPException(502,'Unexpected image format')
                result={'image':encoded,'mime':mime,'deployment':'flux-lab','scope':'FLUX text-to-image; three attempts per UTC day across portal users.'}
        elif eid=='05':
            rows=[json.loads(line) for line in body.prompt.splitlines() if line.strip()]
            valid=0
            for row in rows:
                msgs=row.get('messages',[]) if isinstance(row,dict) else []
                if isinstance(msgs,list) and all(isinstance(m,dict) and m.get('role') in ('system','user','assistant') and isinstance(m.get('content'),str) and m['content'].strip() for m in msgs) and {'user','assistant'} <= {m['role'] for m in msgs}: valid+=1
            result={'rows':len(rows),'valid_rows':valid,'scope':'Local JSONL structure validation only; no training job submitted. Service minimum dataset size and pricing must be checked separately.'}
        elif eid=='VS08':
            reserve_service(uid,'search')
            endpoint='https://ossiemate-search-a37bf3fc.search.windows.net'; index='ai103-learning-samples'; params={'api-version':'2024-07-01'}
            h=headers('https://search.azure.com/.default')
            with httpx.Client(timeout=20,headers=h) as c:
                r=c.put(endpoint+'/indexes/'+index,params=params,json={'name':index,'fields':[{'name':'id','type':'Edm.String','key':True},{'name':'content','type':'Edm.String','searchable':True}]}); r.raise_for_status()
                r=c.post(endpoint+'/indexes/'+index+'/docs/index',params=params,json={'value':[{'@search.action':'mergeOrUpload','id':'1','content':'Solar panels generate electricity from sunlight.'},{'@search.action':'mergeOrUpload','id':'2','content':'Water treatment removes contaminants from drinking water.'}]}); r.raise_for_status()
                if not all(x.get('status') for x in r.json().get('value',[])): raise HTTPException(502,'Index ingestion failed')
                r=c.post(endpoint+'/indexes/'+index+'/docs/search',params=params,json={'search':body.prompt or '*','top':2,'queryType':'simple'}); r.raise_for_status()
                result={'result':r.json(),'scope':'Live keyword search over two fixed sample documents; not full knowledge mining pipeline. Newly indexed documents may take time to appear.'}
        else:
            reserve_service(uid,'cu')
            raw=base64.b64decode(body.image,validate=True)
            if len(raw)>500000 or not ((body.mime=='image/png' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (body.mime=='image/jpeg' and raw.startswith(b'\xff\xd8\xff'))): raise HTTPException(422,'Use PNG or JPEG under 500 KB')
            endpoint='https://ai103-agent-lab.services.ai.azure.com'; analyzer='prebuilt-imageSearch'; params={'api-version':'2025-11-01'}
            with httpx.Client(timeout=20,headers=headers('https://cognitiveservices.azure.com/.default')) as c:
                r=c.post(endpoint+'/contentunderstanding/analyzers/'+analyzer+':analyzeBinary',params=params,headers={'Content-Type':'application/octet-stream'},content=raw); r.raise_for_status()
                result={'status':r.status_code,'operation_location':r.headers.get('operation-location'),'scope':'Experimental analyzer submission only; API/analyzer compatibility unverified. No polling or multimodal extraction implemented.'}
        result['duration_seconds']=round(perf_counter()-start,3); return result
    except HTTPException: raise
    except (ValueError,TypeError,AttributeError): raise HTTPException(422,'Invalid input') from None
    except httpx.HTTPStatusError as e: raise HTTPException(502,'Azure HTTP '+str(e.response.status_code)) from None
    except Exception: raise HTTPException(502,'Service execution failed') from None
    finally: slots.release()
