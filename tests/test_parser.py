import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core import parser


def test_sudachi_reading_known():
    assert parser.sudachi_reading("太郎") == "タロウ"


def test_sudachi_reading_latin():
    # Sudachi handles latin letters by transliteration
    assert parser.sudachi_reading("John") == "ジョン"
