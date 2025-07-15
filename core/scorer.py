from __future__ import annotations
from typing import List
from .normalize import normalize_kana, normalize_for_keypuncher_check
from . import parser
import time
import os
import asyncio
import re
import openai
from functools import lru_cache

client = openai.OpenAI()
async_client = openai.AsyncOpenAI()
# Default model uses GPT-4.1 mini with knowledge cutoff 2025-04-14
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini-2025-04-14")
# Maximum number of unique candidate readings kept
MAX_CANDIDATES = 9

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
    """Return candidate readings for ``name`` using Sudachi and GPT."""
    prompt = f"{name} の読みをカタカナで答えて"
    configs = [(0.0, 3), (0.7, 5)]

    cand: List[str] = []
    seen = set()

    sudachi = parser.sudachi_reading(name)
    if sudachi:
        norm = normalize_kana(sudachi)
        seen.add(norm)
        cand.append(norm)

    for temp, n in configs:
        res = _call_with_backoff(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temp,
            n=n,
            presence_penalty=1.0,
        )
        for c in res.choices:
            norm = _clean_reading(c.message.content.strip())
            if norm not in seen:
                seen.add(norm)
                cand.append(norm)
            if len(cand) >= MAX_CANDIDATES:
                break
        if len(cand) >= MAX_CANDIDATES:
            break
    return cand


async def async_gpt_candidates(name: str) -> List[str]:
    """Asynchronous version of ``gpt_candidates``."""
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

    sudachi = parser.sudachi_reading(name)
    if sudachi:
        norm = normalize_kana(sudachi)
        seen.add(norm)
        cand.append(norm)

    for res in results:
        for c in res.choices:
            norm = _clean_reading(c.message.content.strip())
            if norm not in seen:
                seen.add(norm)
                cand.append(norm)
            if len(cand) >= MAX_CANDIDATES:
                break
        if len(cand) >= MAX_CANDIDATES:
            break
    return cand


def calc_confidence(
    row_reading: str, candidates: List[str], sudachi: str | None = None
) -> tuple[int, str]:
    """Return confidence percentage and short reason.

    ``candidates`` must be in the same order returned by
    :func:`gpt_candidates`, i.e. Sudachi's reading first (if present)
    followed by GPT results.
    """

    target = normalize_for_keypuncher_check(row_reading)

    sudachi_norm = (
        normalize_for_keypuncher_check(sudachi) if sudachi else None
    )

    # dictionary match
    if sudachi_norm and target == sudachi_norm:
        return 100, "辞書候補一致"

    gpt_index = 0
    for cand in candidates:
        cand_norm = normalize_for_keypuncher_check(cand)
        if sudachi_norm and cand_norm == sudachi_norm:
            # skip sudachi candidate already handled
            continue
        gpt_index += 1
        if target == cand_norm:
            if gpt_index == 1:
                return 85, "候補1位一致"
            elif gpt_index == 2:
                return 80, "候補2位一致"
            elif gpt_index == 3:
                return 70, "候補3位一致"
            elif gpt_index <= 5:
                return 60, "5位内一致"
            break

    return 0, "候補外･要確認"
