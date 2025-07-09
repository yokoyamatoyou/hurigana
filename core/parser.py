from __future__ import annotations
from sudachipy import dictionary, tokenizer
from functools import lru_cache

# Initialize Sudachi tokenizer with full dictionary once
TOKENIZER = dictionary.Dictionary(dict="full").create()
MODE = tokenizer.Tokenizer.SplitMode.C


@lru_cache(maxsize=1024)
def sudachi_reading(name: str) -> str | None:
    """Return katakana reading for `name` using SudachiPy."""
    if not name:
        return None
    morps = TOKENIZER.tokenize(name, MODE)
    filtered = [m for m in morps if m.part_of_speech()[0] != "空白"]
    if not filtered:
        return None
    return "".join(m.reading_form() for m in filtered) or None
