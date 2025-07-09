from __future__ import annotations
import unicodedata


def normalize_kana(text: str | None) -> str:
    """Return normalized kana for comparison.

    Converts half-width characters to full-width and removes spaces.
    """
    if not text:
        return ""
    out = unicodedata.normalize("NFKC", text)
    return out.replace(" ", "").replace("　", "")
