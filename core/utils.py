from __future__ import annotations
import pandas as pd
from io import BytesIO
from . import parser, scorer, db
from .normalize import normalize_for_keypuncher_check
import sqlite3
import asyncio
from asyncio import Semaphore

from typing import Callable, Optional


def process_dataframe(
    df: pd.DataFrame,
    name_col: str,
    furi_col: str,
    on_progress: Optional[Callable[[int, int], None]] = None,
    db_conn: sqlite3.Connection | None = None,
    batch_size: int = 50,
) -> pd.DataFrame:
    """Process DataFrame rows in batches and append confidence columns.

    Duplicate names are consolidated globally so the GPT API is called only
    once per unique value, mirroring ``async_process_dataframe``.

    Parameters
    ----------
    df : pd.DataFrame
        Input data.
    name_col : str
        Name column.
    furi_col : str
        Furigana column.
    on_progress : Callable[[int, int], None] | None
        Optional callback receiving processed and total counts.
    db_conn : sqlite3.Connection | None
        Optional database connection for caching.
    batch_size : int, default 50
        Number of rows processed per batch.
    """
    confs: list[int | None] = [None] * len(df)
    reasons: list[str | None] = [None] * len(df)

    total = len(df)
    processed = 0
    pending: dict[str, dict[str, list | str | None]] = {}

    has_furi = furi_col in df.columns
    readings = df[furi_col] if has_furi else ["" for _ in range(len(df))]

    # first pass: handle cached/sudachi results and gather GPT targets
    for idx, (name_val, reading_val) in enumerate(zip(df[name_col], readings)):
        name = "" if pd.isna(name_val) else str(name_val)
        reading = "" if pd.isna(reading_val) else str(reading_val)

        if not name or len(name) > 50:
            confs[idx] = 0
            reasons[idx] = "長すぎる"
            processed += 1
            if on_progress:
                on_progress(processed, total)
            continue

        if db_conn:
            cached = db.get_reading(name, reading, db_conn)
            if cached:
                confs[idx] = cached[0]
                reasons[idx] = cached[1]
                processed += 1
                if on_progress:
                    on_progress(processed, total)
                continue

        sudachi_kana = parser.sudachi_reading(name)
        if sudachi_kana and normalize_for_keypuncher_check(sudachi_kana) == normalize_for_keypuncher_check(reading):
            confs[idx] = 100
            reasons[idx] = "辞書候補一致"
            processed += 1
            if on_progress:
                on_progress(processed, total)
            continue

        entry = pending.setdefault(name, {"rows": [], "sudachi": sudachi_kana})
        entry["rows"].append((idx, reading))

    if pending:
        names = list(pending)
        for start in range(0, len(names), batch_size):
            chunk = names[start:start + batch_size]
            results = [scorer.gpt_candidates(n) for n in chunk]
            rows_to_save = []
            for name, cands in zip(chunk, results):
                info = pending[name]
                sudachi = info.get("sudachi")
                for idx, reading in info["rows"]:
                    conf, reason = scorer.calc_confidence(reading, cands, sudachi)
                    confs[idx] = conf
                    reasons[idx] = reason
                    if db_conn:
                        rows_to_save.append((name, reading, conf, reason))
                    processed += 1
                    if on_progress:
                        on_progress(processed, total)
            if db_conn and rows_to_save:
                db.save_many_readings(rows_to_save, db_conn)

    df = df.copy()
    df["信頼度"] = confs
    df["理由"] = reasons
    return df


async def async_process_dataframe(
    df: pd.DataFrame,
    name_col: str,
    furi_col: str,
    on_progress: Optional[Callable[[int, int], None]] = None,
    db_conn: sqlite3.Connection | None = None,
    batch_size: int = 50,
    concurrency: int = 10,
) -> pd.DataFrame:
    """Asynchronous version of ``process_dataframe`` with limited concurrency.

    Names are deduplicated globally so GPT is called only once per unique name,
    greatly reducing runtime when many duplicates exist.
    """
    confs: list[int | None] = [None] * len(df)
    reasons: list[str | None] = [None] * len(df)
    total = len(df)
    processed = 0
    sem = Semaphore(concurrency)

    async def fetch_candidates(name: str) -> tuple[str, list[str]]:
        async with sem:
            try:
                cands = await scorer.async_gpt_candidates(name)
            except Exception:
                cands = []
        return name, cands

    pending: dict[str, dict[str, list | str | None]] = {}

    has_furi = furi_col in df.columns
    readings = df[furi_col] if has_furi else ["" for _ in range(len(df))]

    # first pass: handle cached/sudachi results and collect GPT targets
    for idx, (name_val, reading_val) in enumerate(zip(df[name_col], readings)):
        name = "" if pd.isna(name_val) else str(name_val)
        reading = "" if pd.isna(reading_val) else str(reading_val)

        if not name or len(name) > 50:
            confs[idx] = 0
            reasons[idx] = "長すぎる"
            processed += 1
            if on_progress:
                on_progress(processed, total)
            continue

        if db_conn:
            cached = db.get_reading(name, reading, db_conn)
            if cached:
                confs[idx] = cached[0]
                reasons[idx] = cached[1]
                processed += 1
                if on_progress:
                    on_progress(processed, total)
                continue

        sudachi_kana = parser.sudachi_reading(name)
        if sudachi_kana and normalize_for_keypuncher_check(sudachi_kana) == normalize_for_keypuncher_check(reading):
            confs[idx] = 100
            reasons[idx] = "辞書候補一致"
            processed += 1
            if on_progress:
                on_progress(processed, total)
            continue

        entry = pending.setdefault(name, {"rows": [], "sudachi": sudachi_kana})
        entry["rows"].append((idx, reading))

    if pending:
        names = list(pending)
        for start in range(0, len(names), batch_size):
            chunk = names[start:start + batch_size]
            tasks = [fetch_candidates(n) for n in chunk]
            rows_to_save = []

            for coro in asyncio.as_completed(tasks):
                name, candidates = await coro
                info = pending[name]
                sudachi = info.get("sudachi")
                for idx, reading in info["rows"]:
                    conf, reason = scorer.calc_confidence(reading, candidates, sudachi)
                    confs[idx] = conf
                    reasons[idx] = reason
                    if db_conn:
                        rows_to_save.append((name, reading, conf, reason))
                    processed += 1
                    if on_progress:
                        on_progress(processed, total)
            if db_conn and rows_to_save:
                db.save_many_readings(rows_to_save, db_conn)

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
        with pd.ExcelWriter(
            buf, engine="xlsxwriter", engine_kwargs={"options": {"constant_memory": True}}
        ) as writer:
            df.to_excel(writer, index=False)
        return buf.getvalue()
