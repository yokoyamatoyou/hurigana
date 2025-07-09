import asyncio
from core import parser
from core.scorer import _acall_with_backoff, _clean_reading, DEFAULT_MODEL

CONFIGS = [(0.0, 3), (0.2, 5), (0.5, 5)]

names = [
    ("野々村　美枝子", "ﾉﾉﾑﾗ ﾐｴｺ"),
    ("余村　喜美子", "ﾖﾑﾗ ｷﾐｺ"),
    ("立石　れい子", "ﾀﾃｲｼ ﾚｲｺ"),
    ("林　たき子", "ﾊﾔｼ ﾀｷｺ"),
    ("林　孝子", "ﾊﾔｼ ﾀｶｺ"),
    ("鈴木　幸佳", "ｽｽﾞｷ ﾕｷｶ"),
    ("鈴木　昇", "ｽｽﾞｷ ﾉﾎﾞﾙ"),
    ("鈴木　昇", "ｽｽﾞｷ ﾉﾎﾞﾙ"),
    ("蓮井　悦子", "ﾊｽｲ ｴﾂｺ"),
    ("浪越　久子", "ﾅﾐｺｼ ﾋｻｺ"),
    ("澁谷　千加子", "ｼﾌﾞﾀﾆ ﾁｶｺ"),
    ("澤　富二子", "ｻﾜ ﾌｼﾞｺ"),
    ("濱崎　勝彦", "ﾊﾏｻﾞｷ ｶﾂﾋｺ"),
    ("當山　治行", "ﾄｳﾔﾏ ﾊﾙﾕｷ"),
    ("舩津　玲子", "ﾌﾅﾂ ﾚｲｺ"),
    ("雜賀　キヨヱ", "ｻｲｶ ｷﾖｴ"),
    ("栁瀬　愛子", "ﾔﾅｾ ｱｲｺ"),
    ("髙安　光子", "ﾀｶﾔｽ ﾐﾂｺ"),
    ("髙岡　謙二", "ﾀｶｵｶ ｹﾝｼﾞ"),
    ("髙橋　秀徳", "ﾀｶﾊｼ ﾋﾃﾞﾉﾘ"),
]

async def fetch(name: str):
    prompt = f"{name} の読みをカタカナで答えて"
    steps = []
    seen = set()
    unique = []
    for temp, n in CONFIGS:
        res = await _acall_with_backoff(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temp,
            n=n,
        )
        cands = [_clean_reading(c.message.content.strip()) for c in res.choices]
        steps.append((temp, cands))
        for c in cands:
            if c not in seen:
                seen.add(c)
                unique.append(c)
    return steps, unique

async def main():
    for name, furi in names:
        steps, unique = await fetch(name)
        print(f"名前: {name}\n入力フリガナ: {furi}")
        print(f"Sudachi: {parser.sudachi_reading(name)}")
        for temp, cands in steps:
            print(f"temperature {temp}: {', '.join(cands)}")
        print(f"unique candidates: {', '.join(unique)}")
        print('-'*40)

if __name__ == '__main__':
    asyncio.run(main())
