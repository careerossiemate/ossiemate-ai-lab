"""Select supported Content Understanding analyzers for bounded synthetic uploads."""
import io
import wave
from fastapi import HTTPException

def choose_analyzer(exercise, mime, raw):
    if not raw or len(raw)>500000:
        raise HTTPException(422,'Upload a synthetic file under 500 KB')
    if mime=='image/png' and raw.startswith(b'\x89PNG\r\n\x1a\n') or mime=='image/jpeg' and raw.startswith(b'\xff\xd8\xff'):
        return 'prebuilt-imageSearch',{}
    if exercise=='VS05' and mime=='application/pdf' and raw.startswith(b'%PDF-'):
        return 'prebuilt-documentSearch',{'range':'1'}
    if exercise=='VS05' and mime in ('audio/wav','audio/x-wav','audio/wave'):
        try:
            with wave.open(io.BytesIO(raw),'rb') as wav:
                frames=wav.getnframes(); rate=wav.getframerate()
                if not rate or not frames or frames/rate>15 or wav.getcomptype()!='NONE' or wav.getnchannels()!=1 or wav.getsampwidth()!=2 or not 8000<=rate<=48000:
                    raise ValueError('Unsupported WAV')
                if len(wav.readframes(frames))!=frames*2: raise ValueError('Truncated WAV')
        except (ValueError,EOFError,wave.Error):
            raise HTTPException(422,'Use mono PCM16 WAV, 8-48 kHz, maximum 15 seconds') from None
        return 'prebuilt-audioSearch',{}
    raise HTTPException(422,'Use PNG/JPEG; VS05 also supports first-page PDF and short PCM WAV')
