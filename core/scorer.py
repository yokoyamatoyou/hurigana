from __future__ import annotations
from typing import List
import time
import os
import asyncio
import openai
from functools import lru_cache

client = openai.OpenAI()
async_client = openai.AsyncOpenAI()
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _call_with_backoff(**kwargs):
    """Call OpenAI API with exponential backoff on rate limits."""
    delay = 1
    for _ in range(5):
        try:
            return client.chat.completions.create(**kwargs)
        except (openai.RateLimitError, openai.OpenAIError):
            time.sleep(delay)
            delay *= 2
    return client.chat.completions.create(**kwargs)


async def _acall_with_backoff(**kwargs):
    """Async version of ``_call_with_backoff``."""
    delay = 1
    for _ in range(5):
        try:
            return await async_client.chat.completions.create(**kwargs)
        except (openai.RateLimitError, openai.OpenAIError):
            await asyncio.sleep(delay)
            delay *= 2
    return await async_client.chat.completions.create(**kwargs)


@lru_cache(maxsize=128)
def gpt_candidates(name: str) -> List[str]:
    """Return candidate readings for a name using two-phase GPT calls."""
    # phase 1: deterministic top reading
    prompt1 = f"{name} の読みをカタカナで1つだけ答えて"
    res1 = _call_with_backoff(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt1}],
        temperature=0.0,
        logprobs=5,
        n=1,
    )
    top = res1.choices[0].message.content.strip()

    # phase 2: up to 5 candidates
    prompt2 = f"{name} の読みをカタカナで答えて"
    res2 = _call_with_backoff(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt2}],
        temperature=0.7,
        top_p=1.0,
        n=5,
    )
    cand = [c.message.content.strip() for c in res2.choices]
    if top not in cand:
        cand.insert(0, top)
    # deduplicate while preserving order
    seen = set()
    uniq: List[str] = []
    for c in cand:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    uniq = uniq[:5]
    return uniq


async def async_gpt_candidates(name: str) -> List[str]:
    """Async version of ``gpt_candidates``."""
    # phase 1: deterministic top reading
    prompt1 = f"{name} の読みをカタカナで1つだけ答えて"
    res1 = await _acall_with_backoff(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt1}],
        temperature=0.0,
        logprobs=5,
        n=1,
    )
    top = res1.choices[0].message.content.strip()

    # phase 2: up to 5 candidates
    prompt2 = f"{name} の読みをカタカナで答えて"
    res2 = await _acall_with_backoff(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt2}],
        temperature=0.7,
        top_p=1.0,
        n=5,
    )
    cand = [c.message.content.strip() for c in res2.choices]
    if top not in cand:
        cand.insert(0, top)
    seen = set()
    uniq: List[str] = []
    for c in cand:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    uniq = uniq[:5]
    return uniq


def calc_confidence(
    row_reading: str, candidates: List[str]
) -> tuple[int, str]:
    """Return confidence percentage and short reason."""
    for idx, reading in enumerate(candidates, start=1):
        if row_reading == reading:
            if idx == 1:
                return 85, "候補1位一致"
            elif idx <= 3:
                return 70, "3位内一致"
            else:
                return 60, "5位内一致"
    return 30, "候補外･要確認"
