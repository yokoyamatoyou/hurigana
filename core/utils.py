from __future__ import annotations
import pandas as pd
from io import BytesIO
from . import parser, scorer


from typing import Callable, Optional


def process_dataframe(
    df: pd.DataFrame,
    name_col: str,
    furi_col: str,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> pd.DataFrame:
    """Process DataFrame rows in batches and append confidence columns."""
    confs: list[int] = []
    reasons: list[str] = []

    total = len(df)
    processed = 0
    for start in range(0, total, 50):
        batch = df.iloc[start : start + 50]
        for _, row in batch.iterrows():
            name = str(row[name_col])
            if len(name) > 50:
                confs.append(0)
                reasons.append("長すぎる")
                processed += 1
                if on_progress:
                    on_progress(processed, total)
                continue
            reading = str(row[furi_col]) if furi_col in df.columns else ""
            sudachi_kana = parser.sudachi_reading(name)
            if sudachi_kana and sudachi_kana == reading:
                confs.append(95)
                reasons.append("辞書候補1位一致")
                processed += 1
                if on_progress:
                    on_progress(processed, total)
                continue

            try:
                candidates = scorer.gpt_candidates(name)
            except Exception:
                candidates = []
            conf, reason = scorer.calc_confidence(reading, candidates)
            confs.append(conf)
            reasons.append(reason)
            processed += 1
            if on_progress:
                on_progress(processed, total)

    df = df.copy()
    df["信頼度"] = confs
    df["理由"] = reasons
    return df


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return buf.getvalue()
