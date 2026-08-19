import asyncio
from typing import AsyncGenerator, Literal
from openai import AsyncOpenAI
from config import get_settings
from models.chat import THINKING_BUDGETS, ThinkingLevel

# Token event types
TokenType = Literal["thinking", "content", "done", "error"]


def _get_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(
        api_key=settings.nvidia_api_key,
        base_url=settings.nvidia_base_url,
    )


async def stream_completion(
    messages: list[dict],
    thinking_level: ThinkingLevel = "medium",
) -> AsyncGenerator[tuple[TokenType, str], None]:
    """
    Stream a completion from the NVIDIA API.
    Yields (token_type, text) tuples:
      - ("thinking", chunk)  – reasoning/chain-of-thought tokens
      - ("content", chunk)   – main response tokens
      - ("done", "")         – stream finished normally
      - ("error", message)   – something went wrong
    """
    settings = get_settings()
    client = _get_client()
    max_tokens = THINKING_BUDGETS.get(thinking_level, 4096)

    try:
        stream = await client.chat.completions.create(
            model=settings.nvidia_model,
            messages=messages,
            temperature=1,
            top_p=0.95,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            # reasoning_content is the chain-of-thought field from inkling
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                yield ("thinking", reasoning)

            if delta.content:
                yield ("content", delta.content)

        yield ("done", "")

    except asyncio.CancelledError:
        yield ("done", "")
    except Exception as e:
        yield ("error", str(e))
