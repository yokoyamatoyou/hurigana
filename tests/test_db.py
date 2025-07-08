from pathlib import Path
import pandas as pd
from core import db
from core.utils import process_dataframe
from unittest.mock import patch

def test_db_round_trip(tmp_path):
    path = tmp_path / 'cache.db'
    conn = db.init_db(path)
    db.save_reading('太郎', 'タロウ', 90, 'cached', conn)
    assert db.get_reading('太郎', 'タロウ', conn) == (90, 'cached')


def test_save_many_readings(tmp_path):
    conn = db.init_db(tmp_path / 'many.db')
    rows = [
        ('太郎', 'タロウ', 80, 'r1'),
        ('花子', 'ハナコ', 85, 'r2'),
    ]
    db.save_many_readings(rows, conn)
    assert db.get_reading('太郎', 'タロウ', conn) == (80, 'r1')
    assert db.get_reading('花子', 'ハナコ', conn) == (85, 'r2')


def test_init_db_uses_env_var(tmp_path, monkeypatch):
    path = tmp_path / 'sub' / 'c.db'
    monkeypatch.setenv('FURIGANA_DB', str(path))
    conn = db.init_db()
    assert Path(conn.execute('PRAGMA database_list').fetchone()[2]) == path


def test_process_dataframe_uses_cache(tmp_path):
    path = tmp_path / 'c.db'
    conn = db.init_db(path)
    db.save_reading('太郎', 'タロウ', 88, 'cache', conn)
    df = pd.DataFrame({'名前': ['太郎'], 'フリガナ': ['タロウ']})
    with patch('core.utils.parser.sudachi_reading') as p_mock, patch('core.utils.scorer.gpt_candidates') as g_mock:
        out = process_dataframe(df, '名前', 'フリガナ', db_conn=conn)
    assert out['信頼度'][0] == 88
    assert out['理由'][0] == 'cache'
    p_mock.assert_not_called()
    g_mock.assert_not_called()

