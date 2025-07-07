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
        batch = df.iloc[start:start + 50]
        for _, row in batch.iterrows():
            name_val = row[name_col]
            name = "" if pd.isna(name_val) else str(name_val)
            if not name or len(name) > 50:
                confs.append(0)
                reasons.append("長すぎる")
                processed += 1
                if on_progress:
                    on_progress(processed, total)
                continue
            reading_val = row[furi_col] if furi_col in df.columns else ""
            reading = "" if pd.isna(reading_val) else str(reading_val)
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


def to_excel_bytes(
    df: pd.DataFrame, template_bytes: bytes | None = None
) -> bytes:
    """Return Excel bytes for ``df`` using ``openpyxl``.

    If ``template_bytes`` is provided the workbook is loaded and overwritten
    with ``df`` while preserving existing formatting."""
    if template_bytes:
        buf = BytesIO(template_bytes)
        with pd.ExcelWriter(
            buf,
            engine="openpyxl",
            mode="a",
            if_sheet_exists="replace",
        ) as writer:
            sheet = (
                writer.book.sheetnames[0]
                if writer.book.sheetnames
                else "Sheet1"
            )
            df.to_excel(writer, index=False, sheet_name=sheet)
        buf.seek(0)
        return buf.getvalue()
    else:
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        return buf.getvalue()
