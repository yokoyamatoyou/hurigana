from __future__ import annotations
from sudachipy import dictionary, tokenizer

# Initialize Sudachi tokenizer with full dictionary once
TOKENIZER = dictionary.Dictionary(dict_type="full").create()
MODE = tokenizer.Tokenizer.SplitMode.C


def sudachi_reading(name: str) -> str | None:
    """Return katakana reading for `name` using SudachiPy."""
    if not name:
        return None
    morps = TOKENIZER.tokenize(name, MODE)
    if not morps:
        return None
    return "".join(m.reading_form() for m in morps) or None
