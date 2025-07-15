from __future__ import annotations
from typing import List
from .normalize import (
    normalize_kana,
    normalize_for_keypuncher_check,
    strip_voicing,
)
import time
import os
import asyncio
import re
import openai
from functools import lru_cache

client = openai.OpenAI()
async_client = openai.AsyncOpenAI()
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini-2025-04-14")

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
def gpt_candidates(name: str, exclude: str | None = None) -> List[str]:
    """Return candidate readings using multi-temperature prompts."""
    prompt = f"{name} の読みをカタカナで答えて"
    configs = [(0.0, 3), (0.7, 5)]

    cand: List[str] = []
    seen = set()
    if exclude:
        seen.add(normalize_kana(exclude))
    for temp, n in configs:
        res = _call_with_backoff(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temp,
            n=n,
            presence_penalty=1.0,
        )
        count = 0
        for c in res.choices:
            norm = _clean_reading(c.message.content.strip())
            if norm not in seen:
                seen.add(norm)
                cand.append(norm)
                count += 1
            if count >= n:
                break
    return cand


async def async_gpt_candidates(name: str, exclude: str | None = None) -> List[str]:
    """Async version of ``gpt_candidates`` using multiple temperatures."""
    prompt = f"{name} の読みをカタカナで答えて"
    configs = [(0.0, 3), (0.7, 5)]

    tasks = [
        _acall_with_backoff(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temp,
            n=n,
            presence_penalty=1.0,
        )
        for temp, n in configs
    ]
    results = await asyncio.gather(*tasks)

    cand: List[str] = []
    seen = set()
    if exclude:
        seen.add(normalize_kana(exclude))
    for res, (_, n) in zip(results, configs):
        count = 0
        for c in res.choices:
            norm = _clean_reading(c.message.content.strip())
            if norm not in seen:
                seen.add(norm)
                cand.append(norm)
                count += 1
            if count >= n:
                break
    return cand


def calc_confidence(
    row_reading: str, candidates: List[str], has_sudachi: bool = False
) -> tuple[int, str]:
    """Return confidence percentage and short reason."""

    target = normalize_for_keypuncher_check(row_reading)
    target_base = strip_voicing(row_reading)

    offset = 1 if has_sudachi else 0
    for idx, reading in enumerate(candidates, start=1):
        cand_norm = normalize_for_keypuncher_check(reading)
        if target == cand_norm or target_base == strip_voicing(reading):
            if has_sudachi and idx == 1:
                return 100, "辞書候補1位一致"
            rank = idx - offset
            if 1 <= rank <= 3:
                scores = {1: 99, 2: 90, 3: 80}
                return scores[rank], f"候補{rank}位一致"
            elif 4 <= rank <= 8:
                scores = {1: 70, 2: 60, 3: 50, 4: 40, 5: 30}
                return scores[rank - 3], "候補一致"
    return 0, "候補外･要確認"
