"""
Context window manager for M00 chatbot.

Manages large conversation histories to fit within model context limits.
Strategy:
  1. Pull full chat history from MongoDB (authoritative source of truth).
  2. Estimate token count (fast ~4 chars/token heuristic).
  3. If total fits within budget, pass everything as-is.
  4. If too long, apply a "sliding window + summary" strategy:
     - Always keep the system prompt + last N recent messages verbatim.
     - Compress older messages into a rolling summary injected as a system note.

Model context budgets:
  - thinkingmachines/inkling  → 128k context window
    We conservatively budget 100k for history (leaving room for system prompt + output).
  - Any model claiming 1M tokens → use 900k budget for history.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

# ─── Constants ────────────────────────────────────────────────────────────────

# Characters per token (rough heuristic for English text)
CHARS_PER_TOKEN = 4

# How many tokens to reserve for the system prompt + tool contexts + output
SYSTEM_RESERVE_TOKENS = 8_000

# Maximum history tokens to feed the model.
# inkling advertises 128k context; we use 100k for history.
# If you switch to a true 1M-context model, bump this to 900_000.
MAX_HISTORY_TOKENS = 100_000

# Number of most-recent messages to ALWAYS preserve verbatim (never summarized)
VERBATIM_TAIL = 20


def _estimate_tokens(text: str) -> int:
    """Fast token count heuristic: 1 token ≈ 4 characters."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def _msg_tokens(msg: dict) -> int:
    """Estimate tokens in a single message dict {role, content}."""
    # role label costs ~4 tokens in typical tokenizers
    return _estimate_tokens(msg.get("content", "")) + 4


# ─── Main entry point ─────────────────────────────────────────────────────────

async def build_context_messages(
    chat_oid: ObjectId,
    db: AsyncIOMotorDatabase,
    system_prompt: str,
) -> list[dict]:
    """
    Load the full conversation history for `chat_oid` from MongoDB and return
    a list of API-ready message dicts that fit within the model context budget.

    The returned list always starts with the system message.
    """
    # ── 1. Load full history from DB ─────────────────────────────────────────
    cursor = db["messages"].find(
        {"chat_id": chat_oid},
        {"role": 1, "content": 1, "_id": 0},
    ).sort("timestamp", 1)  # oldest first

    all_messages: list[dict] = []
    async for doc in cursor:
        role = doc.get("role", "")
        content = doc.get("content", "") or ""
        if role in ("user", "assistant") and content.strip():
            all_messages.append({"role": role, "content": content})

    if not all_messages:
        return [{"role": "system", "content": system_prompt}]

    # ── 2. Check if everything fits ──────────────────────────────────────────
    system_tokens = _estimate_tokens(system_prompt) + 4
    budget = MAX_HISTORY_TOKENS - system_tokens

    total_history_tokens = sum(_msg_tokens(m) for m in all_messages)

    if total_history_tokens <= budget:
        # Everything fits — pass full history
        print(
            f"[Context] Full history: {len(all_messages)} msgs, "
            f"~{total_history_tokens:,} tokens (budget {budget:,})"
        )
        return [{"role": "system", "content": system_prompt}] + all_messages

    # ── 3. Too long — apply sliding window with summary ──────────────────────
    # Always keep the last VERBATIM_TAIL messages exactly as-is
    tail = all_messages[-VERBATIM_TAIL:]
    head = all_messages[:-VERBATIM_TAIL]

    tail_tokens = sum(_msg_tokens(m) for m in tail)
    head_tokens = sum(_msg_tokens(m) for m in head)

    print(
        f"[Context] History too long ({total_history_tokens:,} tokens). "
        f"Tail: {len(tail)} msgs ({tail_tokens:,} tokens). "
        f"Head: {len(head)} msgs ({head_tokens:,} tokens)."
    )

    # Build a compressed summary of the head messages
    summary_lines = []
    for m in head:
        role_label = "User" if m["role"] == "user" else "Assistant"
        # Truncate very long individual messages in the summary
        content = m["content"]
        if len(content) > 500:
            content = content[:500] + "…"
        summary_lines.append(f"{role_label}: {content}")

    summary_text = (
        "## Earlier Conversation Summary\n"
        "The following is a compressed summary of earlier messages in this conversation "
        "that occurred before the recent messages shown below. Use this context to maintain "
        "continuity but prioritize the recent messages for the current task.\n\n"
        + "\n\n".join(summary_lines)
    )

    summary_tokens = _estimate_tokens(summary_text)
    total_new = system_tokens + summary_tokens + tail_tokens

    print(
        f"[Context] After compression: system={system_tokens:,} "
        f"summary={summary_tokens:,} tail={tail_tokens:,} "
        f"total={total_new:,} tokens"
    )

    # Prepend summary as a system-role message for clarity
    return [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": summary_text},
    ] + tail
