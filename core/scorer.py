from __future__ import annotations
from typing import Dict, List
import time
import openai

client = openai.OpenAI()

# simple in-memory cache of name -> candidate list
_CANDIDATE_CACHE: Dict[str, List[str]] = {}


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


def gpt_candidates(name: str) -> List[str]:
    """Return candidate readings for a name using two-phase GPT calls."""
    if name in _CANDIDATE_CACHE:
        return _CANDIDATE_CACHE[name]
    # phase 1: deterministic top reading
    prompt1 = f"{name} の読みをカタカナで1つだけ答えて"
    res1 = _call_with_backoff(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt1}],
        temperature=0.0,
        logprobs=5,
        n=1,
    )
    top = res1.choices[0].message.content.strip()

    # phase 2: up to 5 candidates
    prompt2 = f"{name} の読みをカタカナで答えて"
    res2 = _call_with_backoff(
        model="gpt-4o-mini",
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
    _CANDIDATE_CACHE[name] = uniq
    return uniq


def calc_confidence(row_reading: str, candidates: List[str]) -> tuple[int, str]:
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
