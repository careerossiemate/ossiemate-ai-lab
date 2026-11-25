import os, base64, json
from datetime import datetime, timezone
from threading import BoundedSemaphore
from time import perf_counter
from uuid import uuid4
from typing import Literal
from azure.core import MatchConditions
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError, ResourceModifiedError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from shared.user_authorization import require_authorised_user
from shared.config import get_settings
from shared.table_storage import get_table_client
from shared.foundry_client import get_foundry_client
router=APIRouter(prefix='/api/expanded')
slots=BoundedSemaphore(1)
LIMITS={'language':(100,10),'translation':(100,10),'document':(20,3),'foundry':(20,3)}
def reserve_service(uid, service):
    table=get_table_client(get_settings().metrics_table)
    daily, perminute=LIMITS[service]
    for _ in range(8):
        now=datetime.now(timezone.utc); minute=now.strftime('%Y%m%d%H%M'); key='quota-v3-'+service+'-'+minute[:8]
        try: row=table.get_entity(uid,key)
        except ResourceNotFoundError:
            try: table.create_entity({'PartitionKey':uid,'RowKey':key,'Requests':0,'Minute':minute,'MinuteRequests':0})
            except ResourceExistsError: pass
            continue
        if row['Minute']>minute: continue
        n=row['MinuteRequests'] if row['Minute']==minute else 0
        if row['Requests']>=daily or n>=perminute: raise HTTPException(429,'Service quota reached; daily reset at 00:00 UTC, minute reset next UTC minute.')
        try:
            table.update_entity({'PartitionKey':uid,'RowKey':key,'Requests':row['Requests']+1,'Minute':minute,'MinuteRequests':n+1},etag=row.metadata['etag'],match_condition=MatchConditions.IfNotModified)
            return
        except ResourceModifiedError: continue
    raise HTTPException(503,'Quota reservation unavailable.')
class Request(BaseModel):
    exercise: Literal['03','04','AG02']
    prompt: str=Field(min_length=1,max_length=2000)
    mode: Literal['chat','file','web']='chat'
@router.get('/capabilities')
def capabilities(user=Depends(require_authorised_user)):
    return {'enabled':os.getenv('LIVE_EXPANDED_ENABLED')=='true','exercises':['03','04','AG02']}
@router.post('/run')
def run(body:Request,user=Depends(require_authorised_user)):
    if os.getenv('LIVE_EXPANDED_ENABLED')!='true': raise HTTPException(503,'Disabled')
    if not slots.acquire(False): raise HTTPException(429,'Service busy')
    start=perf_counter()
    try:
        reserve_service(user['user_id'],'foundry')
        client=get_foundry_client(); model=get_settings().model_deployment
        args={'model':model,'input':body.prompt,'max_output_tokens':512,'store':False}
        if body.exercise=='04':
            if body.mode=='file': args['tools']=[{'type':'file_search','vector_store_ids':['vs_ZaLTkbSapGtkcVTmqMCbL80P'],'max_num_results':2}]
            elif body.mode=='web': args['tools']=[{'type':'web_search'}]
            else: raise HTTPException(422,'Select file or web search')
            args['max_tool_calls']=1
        if body.exercise=='AG02':
            args['tools']=[{'type':'function','name':'calculate_total','description':'Multiply quantity by unit price','parameters':{'type':'object','properties':{'quantity':{'type':'integer'},'unit_price':{'type':'number'}},'required':['quantity','unit_price'],'additionalProperties':False},'strict':True}]
            args['tool_choice']='required'
        response=client.responses.create(**args)
        usage=response.usage; calls=[]; answer=response.output_text
        for item in response.output:
            if item.type.endswith('_call'): calls.append({'type':item.type,'status':getattr(item,'status',None)})
            if body.exercise=='AG02' and item.type=='function_call' and item.name=='calculate_total':
                values=json.loads(item.arguments); q=values['quantity']; price=values['unit_price']
                if not isinstance(q,int) or not 0<=q<=10000 or not 0<=price<=100000: raise HTTPException(422,'Tool arguments outside limits')
                answer=f'Calculated total: {q*price:.2f}'; break
        duration=round(perf_counter()-start,3)
        result={'response':answer,'status':response.status,'tool_calls':calls,'input_tokens':usage.input_tokens if usage else 0,'output_tokens':usage.output_tokens if usage else 0,'duration_seconds':duration,'model':model}
        get_table_client(get_settings().metrics_table).create_entity({'PartitionKey':user['user_id'],'RowKey':'expanded-'+uuid4().hex,'ExerciseId':body.exercise,'DurationSeconds':duration,'InputTokens':result['input_tokens'],'OutputTokens':result['output_tokens']})
        return result
    except HTTPException: raise
    except Exception: raise HTTPException(502,'AI execution failed; check model or tool compatibility.') from None
    finally: slots.release()
