from pathlib import Path

p = Path(__file__).resolve().parent / 'Part5_报告.md'
lines = p.read_text(encoding='utf-8').splitlines()
for n in (32, 45, 87, 142, 171, 172, 173, 174, 175):
    print(n, repr(lines[n - 1]))
