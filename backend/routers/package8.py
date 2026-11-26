import asyncio, base64, io, json, re, wave
from datetime import datetime, timezone
from threading import BoundedSemaphore
from uuid import uuid4
import httpx
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from azure.core.exceptions import ResourceExistsError
from shared.table_storage import get_table_client, create_record, get_record, upsert_record
from shared.blob_storage import upload_blob, download_blob, blob_exists
from shared.auth import get_azure_credential
from shared.user_authorization import require_authorised_user
from routers.remaining import router, headers

import os
ACCOUNT='ossiemate-ai103-eastus2'
BASE=f'https://{ACCOUNT}.services.ai.azure.com/providers/falai/v1/minimax/h3-max-turbo'
VIDEO_DEPLOYMENT=os.getenv('PACKAGE9_VIDEO_DEPLOYMENT','Fal-MiniMax-H3-Max-Turbo')
TABLE='LabConfiguration'
CONTAINER='demonstration-results'
slots=BoundedSemaphore(1)
class Input(BaseModel):
    prompt:str=Field(default='',max_length=500)
    audio:str=Field(default='',max_length=2000000)
    image:str=Field(default='',max_length=700000)
    mime:str=Field(default='image/png',max_length=30)

def reserve(kind,limit,period):
    # Atomic create-only slots, globally shared, never refunded on uncertain submission.
    t=get_table_client(TABLE)
    for i in range(limit):
        try:
            t.create_entity({'PartitionKey':'package8-quota','RowKey':f'{kind}-{period}-{i}'})
            return
        except ResourceExistsError: continue
    raise HTTPException(429,'Package 8 usage allowance exhausted')

def now(): return datetime.now(timezone.utc)
def auth(): return headers('https://cognitiveservices.azure.com/.default')
def wav(body):
    try:
        raw=base64.b64decode(body.audio,validate=True)
        with wave.open(io.BytesIO(raw)) as w:
            if w.getnchannels()!=1 or w.getsampwidth()!=2 or w.getframerate()!=24000 or not 0<w.getnframes()<=720000: raise ValueError()
            pcm=w.readframes(w.getnframes())
        return raw,pcm
    except Exception: raise HTTPException(422,'Use mono PCM16 WAV at 24 kHz, maximum 30 seconds') from None

def checked(r):
    if not r.is_success: raise HTTPException(502,f'Provider HTTP {r.status_code}')
    return r.json()

@router.post('/package8/audio')
def audio(b:Input,user=Depends(require_authorised_user)):
    raw,_=wav(b)
    if not slots.acquire(False): raise HTTPException(429,'Busy')
    try:
        reserve('audio',5,now().strftime('%Y%m%d'))
        with httpx.Client(timeout=60) as c:
            result=checked(c.post(f'https://{ACCOUNT}.openai.azure.com/openai/v1/chat/completions',headers=auth(),json={'model':'audio-lab','modalities':['text','audio'],'audio':{'voice':'alloy','format':'wav'},'messages':[{'role':'user','content':[{'type':'text','text':b.prompt or 'Answer the spoken question briefly.'},{'type':'input_audio','input_audio':{'data':base64.b64encode(raw).decode(),'format':'wav'}}]}],'max_completion_tokens':256}))
        msg=result['choices'][0]['message']; a=msg.get('audio') or {}
        return {'text':msg.get('content') or a.get('transcript'),'audio':a.get('data'),'mime':'audio/wav','usage':result.get('usage')}
    except HTTPException: raise
    except Exception as e: raise HTTPException(502,type(e).__name__) from None
    finally: slots.release()

async def voice_turn(pcm):
    from websockets.asyncio.client import connect
    url=f'wss://{ACCOUNT}.services.ai.azure.com/voice-live/realtime?api-version=2026-04-10&profile=byom-azure-openai-realtime&model=realtime-lab'
    h=await asyncio.to_thread(auth)
    async with connect(url,additional_headers=h,open_timeout=10,close_timeout=2,max_size=2000000) as ws:
        async def send(v): await ws.send(json.dumps(v))
        await send({'type':'session.update','session':{'modalities':['text','audio'],'input_audio_format':'pcm16','output_audio_format':'pcm16','turn_detection':None,'instructions':'Answer briefly in one sentence.'}})
        while True:
            e=json.loads(await ws.recv())
            if e['type']=='error': raise HTTPException(502,'Voice Live session rejected')
            if e['type']=='session.updated': break
        for i in range(0,len(pcm),4800): await send({'type':'input_audio_buffer.append','audio':base64.b64encode(pcm[i:i+4800]).decode()})
        await send({'type':'input_audio_buffer.commit'})
        await send({'type':'response.create'})
        out=bytearray(); text=[]
        while True:
            e=json.loads(await ws.recv()); typ=e['type']
            if typ=='error': raise HTTPException(502,'Voice Live event rejected')
            if typ in ('response.audio.delta','response.output_audio.delta'): out.extend(base64.b64decode(e['delta']))
            if typ in ('response.audio_transcript.delta','response.output_audio_transcript.delta'): text.append(e['delta'])
            if len(out)>1440000: raise HTTPException(502,'Voice output limit exceeded')
            if typ=='response.done':
                if e.get('response',{}).get('status')!='completed' or not out: raise HTTPException(502,'Voice response incomplete')
                break
        buf=io.BytesIO()
        with wave.open(buf,'wb') as w: w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(out)
        return {'text':''.join(text),'audio':base64.b64encode(buf.getvalue()).decode(),'mime':'audio/wav','scope':'Native Voice Live BYOM, single recorded turn'}

@router.post('/package8/voice')
def voice(b:Input,user=Depends(require_authorised_user)):
    _,pcm=wav(b)
    if not slots.acquire(False): raise HTTPException(429,'Busy')
    try:
        reserve('voice',3,now().strftime('%Y%m%d'))
        return asyncio.run(asyncio.wait_for(voice_turn(pcm),60))
    except HTTPException: raise
    except Exception as e: raise HTTPException(502,type(e).__name__) from None
    finally: slots.release()

@router.post('/package8/video')
def video(b:Input,user=Depends(require_authorised_user)):
    if not VIDEO_DEPLOYMENT: raise HTTPException(503,'VS03 deployment unavailable')
    if not b.prompt.strip(): raise HTTPException(422,'Enter a synthetic demonstration prompt')
    if not slots.acquire(False): raise HTTPException(429,'Busy')
    try:
        data={'model':VIDEO_DEPLOYMENT,'prompt':b.prompt,'duration':5,'resolution':'480P','prompt_expansion_mode':'disabled','aspect_ratio':'16:9'}
        route='text-to-video'
        if b.image: raise HTTPException(422,'Image-to-video is deferred until input transport is verified')
        # Conservative allocation AUD 1 per attempted 5-second generation; no refunds.
        reserve('video-day',2,now().strftime('%Y%m%d'));reserve('video-month',5,now().strftime('%Y%m'))
        key=uuid4().hex; uid=user['user_id']
        create_record(TABLE,uid,{'State':'submitting','Kind':'package8-video'},key)
        with httpx.Client(timeout=30) as c: result=checked(c.post(BASE+'/'+route,headers=auth(),json=data))
        rid=result.get('request_id','')
        if not re.fullmatch(r'[\w-]{1,128}',rid): raise HTTPException(502,'Invalid provider job ID')
        upsert_record(TABLE,uid,key,{'ProviderId':rid,'State':'submitted'})
        return {'job':key,'status':'submitted'}
    except HTTPException: raise
    except Exception as e: raise HTTPException(502,type(e).__name__) from None
    finally: slots.release()

@router.get('/package8/video/{key}')
def status(key:str,user=Depends(require_authorised_user)):
    if not re.fullmatch('[a-f0-9]{32}',key): raise HTTPException(404,'Unknown job')
    uid=user['user_id']; row=get_record(TABLE,uid,key)
    if not row or row.get('Kind')!='package8-video': raise HTTPException(404,'Unknown job')
    path=f'package8/{uid}/{key}.mp4'
    if not slots.acquire(False): raise HTTPException(429,'Busy')
    try:
        if blob_exists(CONTAINER,path): return {'job':key,'status':'completed','video':base64.b64encode(download_blob(CONTAINER,path)).decode()}
        rid=row.get('ProviderId')
        if not rid: return {'job':key,'status':'submission uncertain; do not retry automatically'}
        with httpx.Client(timeout=45,follow_redirects=False) as c:
            result=checked(c.get(BASE+'/requests/'+rid+'/status',headers=auth()))
            if result.get('status')!='COMPLETED': return {'job':key,'status':result.get('status','unknown')}
            result=checked(c.get(BASE+'/requests/'+rid,headers=auth()))
            url=httpx.URL(result['video']['url'])
            if url.scheme!='https' or not (url.host==f'{ACCOUNT}.services.ai.azure.com' or url.host=='fal.media' or url.host.endswith('.fal.media')) or url.port not in (None,443): raise HTTPException(502,'Unexpected video download host')
            buf=bytearray()
            with c.stream('GET',url,headers=auth() if url.host==f'{ACCOUNT}.services.ai.azure.com' else {}) as r:
                if not r.is_success: raise HTTPException(502,'Video download failed; redirects are not followed')
                for chunk in r.iter_bytes():
                    buf.extend(chunk)
                    if len(buf)>15000000: raise HTTPException(502,'Video exceeds storage limit')
            if len(buf)<12 or buf[4:8]!=b'ftyp': raise HTTPException(502,'Provider did not return an MP4 file')
            upload_blob(CONTAINER,path,bytes(buf),'video/mp4',overwrite=True)
            upsert_record(TABLE,uid,key,{'State':'completed'})
            return {'job':key,'status':'completed','video':base64.b64encode(buf).decode()}
    except HTTPException: raise
    except Exception as e: raise HTTPException(502,type(e).__name__) from None
    finally: slots.release()
