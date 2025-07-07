import os
import sys

import pandas as pd
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.utils import process_dataframe


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
