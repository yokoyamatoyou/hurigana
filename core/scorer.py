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

# regex for the first katakana sequence; also accepts half/full-width digits
# match contiguous katakana or full/half width digits
_KANA_RE = re.compile(r"[\u30A0-\u30FF\u30FC0-9\uFF10-\uFF19]+")


def _clean_reading(text: str) -> str:
    """Return normalized candidate reading from GPT output."""
    text = text.lstrip()
    parts = _KANA_RE.findall(text)
    if parts:
        text = "".join(parts)
    else:
        text = text.replace(" ", "").replace("　", "")
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
    """Return candidate readings using multi-temperature prompts."""
    prompt = f"{name} の読みをカタカナで答えて"
    configs = [(0.0, 3), (0.2, 5), (0.5, 5)]

    cand: List[str] = []
    seen = set()
    for temp, n in configs:
        res = _call_with_backoff(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temp,
            n=n,
        )
        for c in res.choices:
            norm = _clean_reading(c.message.content.strip())
            if norm not in seen:
                seen.add(norm)
                cand.append(norm)
            if len(cand) >= 13:
                break
        if len(cand) >= 13:
            break
    return cand


async def async_gpt_candidates(name: str) -> List[str]:
    """Async version of ``gpt_candidates`` using multiple temperatures."""
    prompt = f"{name} の読みをカタカナで答えて"
    configs = [(0.0, 3), (0.2, 5), (0.5, 5)]

    tasks = [
        _acall_with_backoff(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temp,
            n=n,
        )
        for temp, n in configs
    ]
    results = await asyncio.gather(*tasks)

    cand: List[str] = []
    seen = set()
    for res in results:
        for c in res.choices:
            norm = _clean_reading(c.message.content.strip())
            if norm not in seen:
                seen.add(norm)
                cand.append(norm)
            if len(cand) >= 13:
                break
        if len(cand) >= 13:
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
