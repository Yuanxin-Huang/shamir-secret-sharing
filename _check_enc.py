from pathlib import Path

root = Path(__file__).resolve().parent
for md in sorted(root.glob('*.md')):
    raw = md.read_bytes()
    bom = raw.startswith(b'\xef\xbb\xbf')
    crlf = raw.count(b'\r\n')
    lf = raw.count(b'\n') - crlf
    print(f'{md.name}: BOM={bom}, CRLF={crlf}, LF-only={lf}')
