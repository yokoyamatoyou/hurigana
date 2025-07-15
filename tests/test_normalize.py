from core.normalize import normalize_for_keypuncher_check


def test_normalize_simple():
    assert normalize_for_keypuncher_check('わたなべ キョウコ') == 'ﾜﾀﾅﾍﾞｷﾖｳｺ'


def test_normalize_table_example1():
    assert normalize_for_keypuncher_check('ババジョウジ') == 'ﾊﾞﾊﾞｼﾞﾖｳｼﾞ'


def test_normalize_table_example2():
    assert normalize_for_keypuncher_check('タカハシダイスケ') == 'ﾀｶﾊｼﾀﾞｲｽｹ'
