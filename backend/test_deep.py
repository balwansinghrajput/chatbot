import asyncio
from services.nvidia import _get_client
from config import get_settings

async def test():
    settings = get_settings()
    client = _get_client()
    available = ['web_search', 'rag']
    prompt = (
        f"Given the user's message: 'Hi'\n"
        f"Determine which external tools are strictly necessary to answer. "
        f"Available tools: {available}. "
        f"If the query is a simple greeting (e.g. 'hi', 'hello'), casual conversation, or a standard coding request that does not require live external data or specific internal documents, reply with exactly 'NONE'. "
        f"Otherwise, reply with a comma-separated list of required tools from the available tools."
    )
    
    response = await client.chat.completions.create(
        model=settings.nvidia_model,
        messages=[{'role':'user', 'content':prompt}],
        temperature=0.1,
        max_tokens=256,
        stream=False,
    )
    print('RAW RESPONSE:')
    print(response)

asyncio.run(test())
