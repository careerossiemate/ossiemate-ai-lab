import os
from time import perf_counter, sleep
from threading import BoundedSemaphore
from uuid import uuid4
import base64
import binascii
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from shared.auth import get_azure_credential
from shared.user_authorization import require_authorised_user
from shared.controlled_execution import reserve
from shared.table_storage import get_table_client
from shared.config import get_settings

router = APIRouter(prefix='/api/live')
slots = BoundedSemaphore(1)
LANG = 'https://ossiemate-lang-a37bf3fc.cognitiveservices.azure.com'
DOC = 'https://ossiemate-doc-a37bf3fc.cognitiveservices.azure.com'
TRANS = 'https://ai103-translator-lab.cognitiveservices.azure.com'
class Request(BaseModel):
    exercise: Literal['LG01','LG07','VS07']
    text: str = Field(default='', max_length=2000)
    target: Literal['en','fr','hi','mr','es','de','ja'] = 'fr'
    source: Literal['auto','en','fr','hi','mr','es','de','ja'] = 'auto'
    romanised: bool = False
    document: str = Field(default='', max_length=1400000)

@router.get('/capabilities')
def capabilities(user=Depends(require_authorised_user)):
    return {'enabled': os.getenv('LIVE_SPECIALISED_ENABLED') == 'true', 'exercises': ['LG01','LG07','VS07']}

@router.post('/run')
def run(body: Request, user=Depends(require_authorised_user)):
    if os.getenv('LIVE_SPECIALISED_ENABLED') != 'true':
        raise HTTPException(503, 'Live specialised services disabled.')
    if user.get('authorised') is not True:
        raise HTTPException(403, 'Access denied.')
    if body.exercise != 'VS07' and not body.text.strip():
        raise HTTPException(422, 'Text required.')
    raw = b''
    if body.exercise == 'VS07':
        try: raw = base64.b64decode(body.document, validate=True)
        except (ValueError, binascii.Error): raise HTTPException(422, 'Invalid document.')
        if not raw.startswith(b'%PDF-') or len(raw)>1000000:
            raise HTTPException(422, 'PDF required, maximum 1 MB.')
    if not slots.acquire(blocking=False): raise HTTPException(429, 'Service busy.')
    start = perf_counter()
    try:
        reserve(user['user_id'])
        token = get_azure_credential().get_token('https://cognitiveservices.azure.com/.default').token
        headers = {'Authorization': 'Bearer '+token}
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            if body.exercise == 'LG01':
                result = {}
                for kind in ('SentimentAnalysis','KeyPhraseExtraction','EntityRecognition','LanguageDetection'):
                    r = client.post(LANG+'/language/:analyze-text', params={'api-version':'2023-04-01'}, headers=headers, json={'kind':kind,'analysisInput':{'documents':[{'id':'1','text':body.text}]}})
                    r.raise_for_status(); result[kind]=r.json()
            elif body.exercise == 'LG07':
                text = body.text
                params = {'api-version':'3.0','to':body.target}
                if body.source != 'auto': params['from'] = body.source
                if body.romanised:
                    if body.source not in ('mr','hi'):
                        raise HTTPException(422,'Select Marathi or Hindi for Romanised input.')
                    r=client.post(TRANS+'/translator/text/v3.0/transliterate',params={'api-version':'3.0','language':body.source,'fromScript':'Latn','toScript':'Deva'},headers=headers,json=[{'Text':text}]); r.raise_for_status()
                    text=r.json()[0]['text']
                r=client.post(TRANS+'/translator/text/v3.0/translate',params=params,headers=headers,json=[{'Text':text}]); r.raise_for_status(); result=r.json()
            else:
                r=client.post(DOC+'/documentintelligence/documentModels/prebuilt-layout:analyze',params={'api-version':'2024-11-30','pages':'1-2'},headers={**headers,'Content-Type':'application/octet-stream'},content=raw); r.raise_for_status()
                location=r.headers.get('operation-location','')
                from urllib.parse import urlsplit
                u=urlsplit(location)
                if u.scheme!='https' or u.netloc!=urlsplit(DOC).netloc or not u.path.startswith('/documentintelligence/'): raise HTTPException(502,'Invalid operation location.')
                for _ in range(15):
                    sleep(2); r=client.get(location,headers=headers); r.raise_for_status(); data=r.json()
                    if data.get('status')=='succeeded':
                        a=data['analyzeResult']; result={'content':a.get('content','')[:20000],'pages':len(a.get('pages',[]))}; break
                    if data.get('status')=='failed': raise HTTPException(502,'Document analysis failed.')
                else: raise HTTPException(504,'Document analysis still pending.')
        duration=round(perf_counter()-start,3)
        get_table_client(get_settings().metrics_table).create_entity({'PartitionKey':user['user_id'],'RowKey':'specialised-'+uuid4().hex,'ExerciseId':body.exercise,'DurationSeconds':duration,'Status':'succeeded'})
        return {'result':result,'duration_seconds':duration}
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, 'Azure service returned HTTP '+str(exc.response.status_code)) from None
    except httpx.RequestError:
        raise HTTPException(502,'Azure service connection failed.') from None
    finally: slots.release()
