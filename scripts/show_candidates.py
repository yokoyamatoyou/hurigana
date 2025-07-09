import asyncio
from core import parser
from core.scorer import _acall_with_backoff, _clean_reading, DEFAULT_MODEL

CONFIGS = [(0.0, 3), (2.0, 5), (2.0, 5)]

# limit to first few names due to runtime constraints
names = [
    ("野々村　美枝子", "ﾉﾉﾑﾗ ﾐｴｺ"),
    ("余村　喜美子", "ﾖﾑﾗ ｷﾐｺ"),
    ("立石　れい子", "ﾀﾃｲｼ ﾚｲｺ"),
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
