import os
import sys

import pandas as pd
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.utils import process_dataframe
from core import scorer


def test_process_dataframe_sudachi_match():
    df = pd.DataFrame({
        '名前': ['太郎', '花子'],
        'フリガナ': ['タロウ', 'ハナコ'],
    })

    with patch('core.utils.scorer.gpt_candidates', return_value=[] ) as mock:
        out = process_dataframe(df, '名前', 'フリガナ')

    assert list(out['信頼度']) == [95, 95]
    assert list(out['理由']) == ['辞書候補1位一致', '辞書候補1位一致']
    assert mock.call_count == 0


def test_process_dataframe_long_name():
    long_name = 'あ' * 51
    df = pd.DataFrame({'名前': [long_name], 'フリガナ': ['']})

    with patch('core.utils.scorer.gpt_candidates') as mock:
        out = process_dataframe(df, '名前', 'フリガナ')

    assert out['信頼度'][0] == 0
    assert out['理由'][0] == '長すぎる'
    assert mock.call_count == 0


def test_process_dataframe_gpt_called():
    df = pd.DataFrame({'名前': ['未知'], 'フリガナ': ['ミチ']})

    with patch('core.utils.parser.sudachi_reading', return_value=None), \
         patch('core.utils.scorer.gpt_candidates', return_value=['ミチ', 'ミチョ']), \
         patch('core.utils.scorer.calc_confidence', wraps=scorer.calc_confidence) as conf_mock:
        out = process_dataframe(df, '名前', 'フリガナ')

    assert out['信頼度'][0] == 85
    assert out['理由'][0] == '候補1位一致'
    conf_mock.assert_called_once()
