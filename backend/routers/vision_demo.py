import base64, binascii, os
from threading import BoundedSemaphore
from time import perf_counter
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from shared.user_authorization import require_authorised_user
from shared.config import get_settings
from shared.foundry_client import get_foundry_client
from routers.expanded import reserve_service
router=APIRouter(prefix='/api/vision-demo')
slots=BoundedSemaphore(1)
class Request(BaseModel):
    prompt: str=Field(min_length=1,max_length=2000)
    image: str=Field(max_length=670000)
    mime: Literal['image/png','image/jpeg']
@router.post('/run')
def run(body:Request,user=Depends(require_authorised_user)):
    if os.getenv('LIVE_EXPANDED_ENABLED')!='true': raise HTTPException(503,'Disabled')
    try: raw=base64.b64decode(body.image,validate=True)
    except (ValueError,binascii.Error): raise HTTPException(422,'Invalid image')
    if len(raw)>500000 or not (raw.startswith(b'\x89PNG\r\n\x1a\n') if body.mime=='image/png' else raw.startswith(b'\xff\xd8\xff')): raise HTTPException(422,'Invalid PNG or JPEG')
    if not slots.acquire(False): raise HTTPException(429,'Service busy')
    start=perf_counter()
    try:
        reserve_service(user['user_id'],'foundry')
        model=get_settings().model_deployment
        r=get_foundry_client().responses.create(model=model,input=[{'role':'user','content':[{'type':'input_text','text':body.prompt},{'type':'input_image','image_url':'data:'+body.mime+';base64,'+body.image,'detail':'low'}]}],max_output_tokens=512,store=False)
        return {'response':r.output_text,'duration_seconds':round(perf_counter()-start,3),'model':model,'status':r.status,'input_tokens':r.usage.input_tokens if r.usage else 0,'output_tokens':r.usage.output_tokens if r.usage else 0}
    except HTTPException: raise
    except Exception: raise HTTPException(502,'Vision execution failed; verify model image-input compatibility.') from None
    finally: slots.release()
