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
LIMITS.update({'search':(10,2),'cu':(5,1),'flux':(3,1),'nativeagent':(3,1),'framework':(3,1),'mcpdemo':(3,1),'a2ademo':(3,1),'speechmcp':(3,1)})
slots=BoundedSemaphore(1)
GUIDES={

'AG06':'Publish a native agent to Teams after tenant administrator approval.',
'AG10':'Configure authenticated remote A2A agent cards and message endpoints.',
'LG03':'Deploy a supported generative audio model after pricing approval.',
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
    return {'experimental':['LG05','AG04','AG03','AG08','AG01','VS02','VS08','VS04','VS05','VS06'],'local_validation':['05'],'blocked':GUIDES}

@router.post('/run')
def run(body:Request,user=Depends(require_authorised_user)):
    eid=body.exercise; uid=user['user_id']; start=perf_counter()
    if eid in GUIDES: raise HTTPException(503,GUIDES[eid])
    if eid not in ('LG05','AG04','AG03','AG08','AG01','VS02','05','VS08','VS04','VS05','VS06'): raise HTTPException(404,'Unknown exercise')
    if not slots.acquire(False): raise HTTPException(429,'Service busy')
    try:
        if eid=='AG04':
            reserve_service('global-knowledge-discovery','search')
            with httpx.Client(timeout=20,headers=headers('https://search.azure.com/.default')) as c:
                r=c.get('https://ossiemate-search-a37bf3fc.search.windows.net/knowledgebases',params={'api-version':'2025-11-01-preview'})
                r.raise_for_status()
                names=[x.get('name') for x in r.json().get('value',[]) if x.get('name')]
                result={'knowledge_bases':names,'scope':'Native knowledge base discovery'}
                if body.prompt.strip():
                    if len(names)!=1: raise HTTPException(409,'Retrieval requires exactly one existing knowledge base; no resources created.')
                    import re
                    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,127}',names[0]): raise HTTPException(502,'Invalid knowledge base name')
                    r=c.post('https://ossiemate-search-a37bf3fc.search.windows.net/knowledgebases/'+names[0]+'/retrieve',params={'api-version':'2025-11-01-preview'},json={'messages':[{'role':'user','content':[{'type':'text','text':body.prompt}]}]})
                    r.raise_for_status()
                    result={'knowledge_base':names[0],'retrieval':r.json(),'scope':'Native retrieval API; existing knowledge base only, no agent binding.'}
        elif eid=='LG05':
            if not body.prompt.strip(): raise HTTPException(422,'Enter speech text')
            reserve_service('global-speech-mcp','speechmcp')
            import asyncio
            from routers.speech_mcp import invoke
            result=asyncio.run(asyncio.wait_for(invoke(body.prompt[:500]),timeout=65))
        elif eid in ('AG03','AG08'):
            if not body.prompt.strip(): raise HTTPException(422,'Enter a question')
            import asyncio
            from routers.agent_tools import mcp_lookup, framework_run
            reserve_service('global-agent-tools-budget','mcpdemo' if eid=='AG03' else 'framework')
            if eid=='AG03':
                result=asyncio.run(asyncio.wait_for(mcp_lookup(body.prompt),timeout=20))
                result['scope']='Real MCP discovery and invocation over stdio; fixed tool selection, not model-directed.'
            else:
                result=asyncio.run(asyncio.wait_for(framework_run(body.prompt),timeout=90))
        elif eid=='AG01':
            if not body.prompt.strip(): raise HTTPException(422,'Enter an agent question')
            reserve_service('global-agent-budget','nativeagent')
            from azure.ai.projects import AIProjectClient
            from azure.ai.projects.models import PromptAgentDefinition
            from uuid import uuid4
            name='ossiemate-lab-'+uuid4().hex[:16]
            with AIProjectClient(endpoint='https://ai103-agent-lab.services.ai.azure.com/api/projects/AI103-agent-lab',credential=get_azure_credential(),retry_total=0,connection_timeout=10,read_timeout=45) as project:
                agent=project.agents.create_version(agent_name=name,definition=PromptAgentDefinition(model='gpt-5-mini-2',instructions='Answer the learning question concisely. Do not invent facts.'))
                cleanup='pending'
                try:
                    with project.get_openai_client() as client:
                        response=client.with_options(timeout=60,max_retries=0).responses.create(input=body.prompt,max_output_tokens=512,extra_body={'agent_reference':{'name':agent.name,'type':'agent_reference'}})
                        result={'response':response.output_text,'agent_name':agent.name,'version':str(agent.version),'scope':'Native Foundry prompt agent, single turn','usage':response.usage.model_dump() if response.usage else None}
                finally:
                    try:
                        project.agents.delete_version(agent_name=agent.name,agent_version=agent.version)
                        cleanup='version deleted'
                    except Exception:
                        cleanup='Version cleanup failed; inspect Foundry agent '+name
                result['cleanup']=cleanup
        elif eid=='VS02':
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
    except (ValueError,TypeError,AttributeError) as e:
        if eid=='AG08': raise HTTPException(502,'AG08 SDK error: '+type(e).__name__) from None
        raise HTTPException(422,'Invalid input') from None
    except httpx.HTTPStatusError as e: raise HTTPException(502,'Azure HTTP '+str(e.response.status_code)) from None
    except Exception as e:
        if eid=='AG08':
            status=getattr(e,'status_code',None)
            suffix=' HTTP '+str(status) if isinstance(status,int) else ''
            raise HTTPException(502,'AG08 execution: '+type(e).__name__+suffix) from None
        raise HTTPException(502,'Service execution failed') from None
    finally: slots.release()


# A bounded, authenticated A2A JSON-RPC 0.3-style teaching endpoint.
# Not a full A2A server: no tasks, streaming, or independent deployment.
@router.get('/a2a/card')
def a2a_card(user=Depends(require_authorised_user)):
    return {'protocolVersion':'0.3.0','name':'Lab Risk Advisor','description':'Single-turn risk advice','url':'https://ca-ai103-backend.wittywave-5f5679ff.australiaeast.azurecontainerapps.io/api/remaining/a2a/message','version':'1.0.0','preferredTransport':'JSONRPC','capabilities':{'streaming':False,'pushNotifications':False},'defaultInputModes':['text/plain'],'defaultOutputModes':['text/plain'],'skills':[{'id':'risk','name':'Risk advice','description':'Identify risks and mitigations','tags':['risk']}],'securitySchemes':{'bearer':{'type':'http','scheme':'bearer'}},'security':[{'bearer':[]}]}

class A2APart(BaseModel):
    kind: str = Field(max_length=10)
    text: str = Field(min_length=1,max_length=1500)
class A2AMessage(BaseModel):
    kind: str = Field(max_length=10)
    role: str = Field(max_length=10)
    messageId: str = Field(min_length=1,max_length=80)
    parts: list[A2APart] = Field(min_length=1,max_length=1)
class A2AParams(BaseModel):
    message: A2AMessage
class A2ARequest(BaseModel):
    jsonrpc: str = Field(max_length=5)
    id: str = Field(min_length=1,max_length=80)
    method: str = Field(max_length=30)
    params: A2AParams

@router.post('/a2a/message')
def a2a_message(body:A2ARequest,user=Depends(require_authorised_user)):
    from uuid import uuid4
    from shared.foundry_client import get_foundry_client
    from shared.config import get_settings
    msg=body.params.message
    if body.jsonrpc!='2.0' or body.method!='message/send' or msg.kind!='message' or msg.role!='user' or msg.parts[0].kind!='text':
        return {'jsonrpc':'2.0','id':body.id,'error':{'code':-32602,'message':'Unsupported message format'}}
    if not slots.acquire(False): raise HTTPException(429,'Service busy')
    try:
        reserve_service('global-a2a-budget','a2ademo')
        started=perf_counter()
        response=get_foundry_client().responses.create(model=get_settings().model_deployment,input=msg.parts[0].text,instructions='Act as a risk advisor. Provide concise risk and mitigation advice. Identify uncertainty.',max_output_tokens=1536,store=False)
        text=(response.output_text or '').strip()
        usage=response.usage.model_dump() if response.usage else None
        diagnostics={'status':response.status,'incomplete_reason':getattr(response.incomplete_details,'reason',None),'usage':usage,'duration_seconds':round(perf_counter()-started,3)}
        if response.status!='completed' or not text:
            return {'jsonrpc':'2.0','id':body.id,'error':{'code':-32001,'message':'Model did not complete a nonempty answer','data':diagnostics}}
        return {'jsonrpc':'2.0','id':body.id,'result':{'kind':'message','role':'agent','messageId':uuid4().hex,'parts':[{'kind':'text','text':text}], 'metadata':diagnostics}}
    except HTTPException: raise
    except Exception as e: raise HTTPException(502,'A2A execution: '+type(e).__name__) from None
    finally: slots.release()

@router.get('/external-readiness/{exercise}')
def external_readiness(exercise: str, user=Depends(require_authorised_user)):
    details = {
        'AG06': {'required': 'Microsoft 365 tenant publishing approval and native agent publication', 'next': 'Verify tenant policy in Microsoft 365 admin center and publish from Foundry only after approval.'},
        'LG03': {'required': 'Approved audio-capable model deployment', 'next': 'Check model catalog and deployment SKU; Azure Speech F0 is not a generative audio model.'},
        'LG06': {'required': 'Approved Voice Live model and streaming authentication', 'next': 'Verify model availability, pricing and session authentication before enabling microphone streaming.'},
        'VS03': {'required': 'Approved video-capable model deployment', 'next': 'Verify regional model availability and per-second pricing before submitting a video job.'},
    }
    if exercise not in details:
        raise HTTPException(404, 'Unknown external exercise')
    return {'exercise': exercise, 'status': 'blocked_pending_approval_or_compatibility', 'live_execution': False, 'inference_performed': False, **details[exercise]}
