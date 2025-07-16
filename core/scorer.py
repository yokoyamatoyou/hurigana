from __future__ import annotations
from typing import List
from .normalize import normalize_kana, normalize_for_keypuncher_check
from . import parser
import time
import os
import asyncio
import re
import openai
import json
from collections import Counter
import Levenshtein
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


class Scorer:
    def get_scored_candidates(self, llm_results: List[str], original_furigana: str) -> dict:
        """Return scored candidate list from multiple LLM results."""

        all_candidates: list[str] = []
        for res_json in llm_results:
            try:
                data = json.loads(res_json)
                if isinstance(data.get("candidates"), list):
                    for candidate in data["candidates"]:
                        if isinstance(candidate, dict) and "furigana" in candidate:
                            all_candidates.append(candidate["furigana"])
            except (json.JSONDecodeError, TypeError):
                continue

        if not all_candidates:
            return self._build_response(
                "error",
                "有効なフリガナ候補を生成できませんでした。",
                original_furigana,
                [],
            )

        counts = Counter(all_candidates)
        unique_candidates = list(counts.keys())
        scored_list = []
        for f in unique_candidates:
            score = self._calculate_score(f, original_furigana, counts[f], len(llm_results))
            scored_list.append({"furigana": f, "score": round(score, 4)})

        scored_list.sort(key=lambda x: x["score"], reverse=True)

        return self._judge(original_furigana, scored_list)

    def _calculate_score(
        self, candidate_furigana: str, original_furigana: str, count: int, total_agents: int
    ) -> float:
        """Calculate score for a single candidate."""

        support_score = count / total_agents
        distance = Levenshtein.distance(candidate_furigana, original_furigana)
        max_len = max(len(candidate_furigana), len(original_furigana))
        similarity_score = (max_len - distance) / max_len if max_len > 0 else 1.0
        return (support_score * 0.7) + (similarity_score * 0.3)

    def _judge(self, original_furigana: str, scored_list: list[dict]) -> dict:
        if not scored_list:
            return self._build_response(
                "error",
                "評価可能な候補がありません。",
                original_furigana,
                [],
            )

        top = scored_list[0]
        original_in_list = any(c["furigana"] == original_furigana for c in scored_list)

        if not original_in_list:
            return self._build_response(
                "error",
                "入力されたフリガナは候補にありません。入力ミスの可能性が非常に高いです。",
                original_furigana,
                scored_list,
            )

        if top["furigana"] == original_furigana:
            return self._build_response(
                "success",
                "入力されたフリガナが最も可能性の高い候補です。",
                original_furigana,
                scored_list,
            )

        return self._build_response(
            "warning",
            f"入力された '{original_furigana}' よりも可能性の高い候補 '{top['furigana']}' があります。",
            original_furigana,
            scored_list,
        )

    def _build_response(self, status: str, message: str, original_furigana: str, candidates: list) -> dict:
        return {
            "status": status,
            "message": message,
            "input_furigana": original_furigana,
            "candidates": candidates,
        }

