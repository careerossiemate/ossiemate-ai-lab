import asyncio, sys, os
from pathlib import Path
from shared.auth import get_foundry_token_provider
from shared.config import get_settings

async def mcp_lookup(prompt):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    params = StdioServerParameters(command=sys.executable, args=[str(Path(__file__).with_name("lab_mcp_server.py"))], env={"PATH":os.environ.get("PATH", "")})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool("lookup_policy", {"topic": prompt[:200]})
            if result.isError:
                raise RuntimeError("MCP tool error")
            return {"tools":[t.name for t in tools.tools], "tool_result":result.model_dump(mode="json")}

async def framework_run(prompt):
    from agent_framework import Agent
    from agent_framework.openai import OpenAIResponsesClient
    from openai import AsyncOpenAI
    settings = get_settings()
    async with AsyncOpenAI(base_url=settings.azure_openai_endpoint, api_key=get_foundry_token_provider(), timeout=60, max_retries=0) as client:
        chat = OpenAIResponsesClient(async_client=client, model=settings.model_deployment)
        agent = Agent(client=chat, name="LabAdvisor", instructions="Answer concisely. Identify uncertainty.", default_options={"max_tokens":512})
        result = await agent.run(prompt)
        return {"response":str(result), "scope":"Microsoft Agent Framework single-turn agent via Responses API"}
