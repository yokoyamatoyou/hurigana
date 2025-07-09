from core import parser
from unittest.mock import patch
import pytest


@pytest.fixture(autouse=True)
def clear_cache():
    parser.sudachi_reading.cache_clear()


def test_sudachi_reading_known():
    assert parser.sudachi_reading("太郎") == "タロウ"


def test_sudachi_reading_latin():
    # Sudachi handles latin letters by transliteration
    assert parser.sudachi_reading("John") == "ジョン"


def test_sudachi_reading_empty():
    assert parser.sudachi_reading("") is None


def test_sudachi_reading_cached():
    with patch.object(parser, "TOKENIZER", wraps=parser.TOKENIZER) as mock_tok:
        first = parser.sudachi_reading("太郎")
        second = parser.sudachi_reading("太郎")

    assert first == "タロウ"
    assert second == "タロウ"
    assert mock_tok.tokenize.call_count == 1


def test_sudachi_reading_ignores_spaces():
    # Sudachi should skip space tokens rather than output "キゴウ"
    assert parser.sudachi_reading("野々村　美枝子") == "ノノムラミエコ"
