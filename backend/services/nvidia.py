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

async def get_completion(
    messages: list[dict],
    model: str | None = None,
    max_tokens: int = 256,
) -> str | None:
    """Non-streaming completion for lightweight agentic tasks."""
    settings = get_settings()
    client = _get_client()
    try:
        # Use a faster, smaller model if available for logic tasks, fallback to main model
        target_model = model or "nvidia/llama-3.1-8b-instruct"
        # We can also just use the main model if preferred, but a fast model is better for internal routing
        # Wait, let's use the main model by default to avoid permission issues with other models on the API key
        target_model = model or settings.nvidia_model
        
        response = await client.chat.completions.create(
            model=target_model,
            messages=messages,
            temperature=0.0,
            max_tokens=max_tokens,
            stream=False,
        )
        if response.choices and response.choices[0].message:
            return response.choices[0].message.content
        return None
    except Exception as e:
        print(f"[NVIDIA Agent] Completion error: {e}")
        return None


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
