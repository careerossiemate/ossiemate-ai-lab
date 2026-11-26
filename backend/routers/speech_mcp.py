import asyncio, os, sys, base64
from pathlib import Path
from xml.sax.saxutils import escape

async def invoke(text):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    # Only pass environment needed for the existing managed identity.
    env={k:v for k,v in os.environ.items() if k in ('PATH','AZURE_CLIENT_ID','IDENTITY_ENDPOINT','IDENTITY_HEADER','MSI_ENDPOINT','MSI_SECRET')}
    params=StdioServerParameters(command=sys.executable,args=['-m','routers.speech_mcp'],env=env)
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            tools=await session.list_tools()
            result=await session.call_tool('synthesize',{'text':text})
            if result.isError: raise RuntimeError('Speech MCP tool failed')
            import json
            data=json.loads(result.content[0].text)
            return {**data,'tools':[t.name for t in tools.tools],'scope':'Local MCP speech tool using Azure Speech REST; not hosted Speech MCP or model-directed selection.'}

if __name__=='__main__':
    import httpx
    from azure.identity import ManagedIdentityCredential
    from mcp.server.fastmcp import FastMCP
    server=FastMCP('Lab Speech')
    @server.tool()
    def synthesize(text: str) -> dict:
        if not text.strip() or len(text)>500: raise ValueError('Text must be 1-500 characters')
        with ManagedIdentityCredential(client_id=os.environ['AZURE_CLIENT_ID']) as cred:
            token=cred.get_token('https://cognitiveservices.azure.com/.default').token
        ssml='<speak version="1.0" xml:lang="en-AU"><voice name="en-AU-NatashaNeural">'+escape(text)+'</voice></speak>'
        with httpx.Client(timeout=30) as c:
            r=c.post('https://ai103-speech-lab.cognitiveservices.azure.com/tts/cognitiveservices/v1',headers={'Authorization':'Bearer '+token,'Content-Type':'application/ssml+xml','X-Microsoft-OutputFormat':'audio-16khz-32kbitrate-mono-mp3'},content=ssml.encode())
            if r.status_code!=200: return {'error':'Speech HTTP '+str(r.status_code)}
            if len(r.content)>1000000: raise ValueError('Audio exceeds limit')
            return {'audio':base64.b64encode(r.content).decode(),'mime':'audio/mpeg'}
    server.run(transport='stdio')
