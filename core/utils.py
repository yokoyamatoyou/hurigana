from __future__ import annotations
from typing import Optional
import pandas as pd
from io import BytesIO
from . import parser, scorer


def process_dataframe(df: pd.DataFrame, name_col: str, furi_col: str) -> pd.DataFrame:
    """Process DataFrame rows and append confidence and reason columns."""
    confs = []
    reasons = []
    for _, row in df.iterrows():
        name = str(row[name_col])
        reading = str(row[furi_col]) if furi_col in df.columns else ""
        sudachi_kana = parser.sudachi_reading(name)
        if sudachi_kana and sudachi_kana == reading:
            confs.append(95)
            reasons.append("辞書候補1位一致")
            continue
        # fallback to LLM
        try:
            candidates = scorer.gpt_readings(name, temperature=0.7)
        except Exception:
            candidates = []
        conf, reason = scorer.calc_confidence(reading, candidates)
        confs.append(conf)
        reasons.append(reason)
    df = df.copy()
    df["信頼度"] = confs
    df["理由"] = reasons
    return df


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return buf.getvalue()
