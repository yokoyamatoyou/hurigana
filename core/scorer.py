from __future__ import annotations
import os
from typing import List, Tuple
import openai

client = openai.OpenAI()


def gpt_readings(name: str, temperature: float) -> List[Tuple[str, float]]:
    """Query GPT model for reading candidates with probabilities."""
    prompt = f"人名『{name}』の読みをカタカナで5件まで『読み|確率%』形式で出力"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        logprobs=True,
        top_p=1.0,
        n=1,
    )
    text = response.choices[0].message.content
    # naive parse: expecting lines like カタカナ|xx%
    result: List[Tuple[str, float]] = []
    for line in text.splitlines():
        if "|" in line:
            reading, prob = line.split("|", 1)
            try:
                prob = float(prob.replace("%", "").strip())
            except ValueError:
                prob = 0.0
            result.append((reading.strip(), prob))
    return result


def calc_confidence(row_reading: str, candidates: List[Tuple[str, float]]) -> tuple[int, str]:
    """Return confidence percentage and short reason."""
    for idx, (reading, _) in enumerate(candidates, start=1):
        if row_reading == reading:
            if idx == 1:
                return 95, "辞書候補1位一致"
            elif idx <= 3:
                return 85, "3位内一致"
            else:
                return 60, "5位内一致"
    return 30, "候補外･要確認"
