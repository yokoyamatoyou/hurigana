from __future__ import annotations
import unicodedata
import jaconv

# mapping for youon expansion used by ``normalize_for_keypuncher_check``
_YOON_BASES = [
    "キ",
    "シ",
    "チ",
    "ニ",
    "ヒ",
    "ミ",
    "リ",
    "ギ",
    "ジ",
    "ヂ",
    "ビ",
    "ピ",
]

MAPPING_YOUON = {
    base + small: base + repl
    for base in _YOON_BASES
    for small, repl in zip("ャュョ", "ヤユヨ")
}


def normalize_kana(text: str | None) -> str:
    """Return normalized kana for comparison.

    Converts half-width characters to full-width and removes spaces.
    """
    if not text:
        return ""
    out = unicodedata.normalize("NFKC", text)
    return out.replace(" ", "").replace("　", "")


def normalize_for_keypuncher_check(text: str | None) -> str:
    """Return reading normalized to keypuncher format.

    This follows the three step process outlined in ``AGENT２.md``:

    1. Normalize to full-width katakana (NFKC) and remove spaces.
    2. Expand yo-on combinations (キャ -> キヤ, etc.).
    3. Convert to half-width with decomposed dakuten/handakuten.
    """

    if not text:
        return ""

    # step1: NFKC -> full-width katakana
    out = unicodedata.normalize("NFKC", text)
    out = out.replace(" ", "").replace("　", "")
    out = "".join(
        chr(ord(ch) + 0x60) if "ぁ" <= ch <= "ゖ" else ch
        for ch in out
    )

    # step2: expand yo-on characters
    for pat, repl in MAPPING_YOUON.items():
        out = out.replace(pat, repl)

    # step3: half-width conversion with dakuten split
    return jaconv.z2h(out, kana=True, digit=True, ascii=False)


def strip_voicing(text: str | None) -> str:
    """Return string without dakuten/handakuten for loose matching."""
    if not text:
        return ""
    out = normalize_kana(text)
    decomposed = unicodedata.normalize("NFD", out)
    return "".join(ch for ch in decomposed if ch not in ("\u3099", "\u309A"))
