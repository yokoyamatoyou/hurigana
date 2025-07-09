from __future__ import annotations
from typing import List
from .normalize import normalize_kana
import time
import os
import asyncio
import re
import openai
from functools import lru_cache

client = openai.OpenAI()
async_client = openai.AsyncOpenAI()
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# simple regex for the first katakana sequence (including spaces, long dash and digits)
_KANA_RE = re.compile(r"[\u30A0-\u30FF\u30FC0-9\s]+")


def _clean_reading(text: str) -> str:
    """Return normalized candidate reading from GPT output."""
    m = _KANA_RE.search(text)
    if m:
        text = m.group(0)
    return normalize_kana(text)


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
    """Return candidate readings using a broader two-phase GPT strategy."""
    # phase 1: deterministic top 3 readings
    prompt1 = f"{name} の読みをカタカナで1つだけ答えて"
    res1 = _call_with_backoff(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt1}],
        temperature=0.0,
        n=3,
    )
    low = [c.message.content.strip() for c in res1.choices]

    # phase 2: 7 additional candidates
    prompt2 = f"{name} の読みをカタカナで答えて"
    res2 = _call_with_backoff(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt2}],
        temperature=0.7,
        top_p=1.0,
        n=7,
    )
    high = [c.message.content.strip() for c in res2.choices]

    cand: List[str] = []
    seen = set()
    for c in low + high:
        norm = _clean_reading(c)
        if norm not in seen:
            seen.add(norm)
            cand.append(norm)
        if len(cand) >= 10:
            break
    return cand


async def async_gpt_candidates(name: str) -> List[str]:
    """Async version of ``gpt_candidates`` using the broader search."""
    prompt1 = f"{name} の読みをカタカナで1つだけ答えて"
    prompt2 = f"{name} の読みをカタカナで答えて"

    res1, res2 = await asyncio.gather(
        _acall_with_backoff(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt1}],
            temperature=0.0,
            n=3,
        ),
        _acall_with_backoff(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt2}],
            temperature=0.7,
            top_p=1.0,
            n=7,
        ),
    )
    low = [c.message.content.strip() for c in res1.choices]
    high = [c.message.content.strip() for c in res2.choices]

    cand: List[str] = []
    seen = set()
    for c in low + high:
        norm = _clean_reading(c)
        if norm not in seen:
            seen.add(norm)
            cand.append(norm)
        if len(cand) >= 10:
            break
    return cand


def calc_confidence(row_reading: str, candidates: List[str]) -> tuple[int, str]:
    """Return confidence percentage and short reason."""
    target = normalize_kana(row_reading)
    for idx, reading in enumerate(candidates, start=1):
        if target == normalize_kana(reading):
            if idx == 1:
                return 85, "候補1位一致"
            elif idx <= 3:
                return 70, "3位内一致"
            elif idx <= 10:
                return 60, "10位内一致"
            else:
                break
    return 30, "候補外･要確認"
