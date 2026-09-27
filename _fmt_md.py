import re
from pathlib import Path

# 需要两侧加空格的 LaTeX 命令
SPACED_CMDS = {
    r'\le', r'\ne', r'\equiv', r'\approx', r'\sim', r'\mapsto',
    r'\in', r'\subset', r'\oplus', r'\times', r'\cdot', r'\bmod',
    r'\cup', r'\ge', r'\ll', r'\longleftarrow',
}
OPEN_BEFORE = {'(', '[', '{', ','}
CLOSE_AFTER = {')', ']', '}', ',', '.', ';', ':'}


def tokenize(s):
    """把公式切成 token：cmd / text(受保护) / ch / sp。"""
    items = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == '\\':
            m = re.match(r'\\([a-zA-Z]+|.)', s[i:])
            tok = m.group(0)
            if tok == r'\text':
                # 连带后面的 { ... } 整块保护，内部原样保留
                j = i + len(tok)
                depth, k = 0, j
                while k < len(s):
                    if s[k] == '{':
                        depth += 1
                    elif s[k] == '}':
                        depth -= 1
                        if depth == 0:
                            k += 1
                            break
                    k += 1
                items.append(['text', s[i:k]])
                i = k
                continue
            items.append(['cmd', tok])
            i += len(tok)
        elif c == ' ':
            items.append(['sp', ' '])
            i += 1
        else:
            items.append(['ch', c])
            i += 1
    return items


def normalize_math(s):
    items = tokenize(s)
    # 1) 标记需要加空格的 token；跟踪 _{...} / ^{...} 分组
    marked = [False] * len(items)
    group_stack = []
    prev_class = None  # val / op / '_' / '^' / opener
    for idx, (t, v) in enumerate(items):
        if t == 'sp':
            continue
        if t == 'ch' and v == '{':
            group_stack.append('script' if prev_class in ('_', '^') else 'normal')
        if t == 'ch' and v == '}':
            if group_stack:
                group_stack.pop()
        in_script = bool(group_stack) and group_stack[-1] == 'script'

        if t == 'cmd' and v in SPACED_CMDS:
            marked[idx] = True
        elif t == 'ch' and v in ('=', '<', '>', '+'):
            marked[idx] = True
        elif t == 'ch' and v == '-':
            # 二元：前一个有意义 token 是“值”；下标组内不拆（如 t-1）
            if prev_class == 'val' and not in_script:
                marked[idx] = True

        if t == 'ch' and v in ('_', '^'):
            prev_class = v
        elif t in ('ch', 'cmd', 'text') and not (t == 'ch' and v in '{}'):
            if marked[idx]:
                prev_class = 'op'
            elif t == 'ch' and v in '([,':
                prev_class = 'opener'
            else:
                prev_class = 'val'

    # 2) 重建：保留原空格，仅给 marked token 补空格
    out = ''
    for idx, (t, v) in enumerate(items):
        if t == 'sp':
            out += ' '
            continue
        if marked[idx]:
            prev_tok = next((items[j][1] for j in range(idx - 1, -1, -1)
                            if items[j][0] != 'sp'), None)
            next_tok = next((items[j][1] for j in range(idx + 1, len(items))
                            if items[j][0] != 'sp'), None)
            if prev_tok is not None and prev_tok[-1] not in OPEN_BEFORE \
                    and not out.endswith(' '):
                out += ' '
            out += v
            if next_tok is not None and next_tok[0] not in CLOSE_AFTER:
                out += ' '
        else:
            out += v

    # 3) 多个连续空格压成一个（\text 保护块除外）
    result = []
    pos = 0
    for mobj in re.finditer(r'\\text\{.*?\}', out):
        segment = re.sub(r' {2,}', ' ', out[pos:mobj.start()])
        result.append(segment)
        result.append(mobj.group(0))
        pos = mobj.end()
    result.append(re.sub(r' {2,}', ' ', out[pos:]))
    return ''.join(result).strip()


INLINE = re.compile(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)')


def transform_text(text):
    lines = text.split('\n')
    out = []
    in_fence = False
    in_display = False
    inline_count = 0
    for line in lines:
        s = line.strip()
        if s.startswith('```'):
            out.append(line)
            in_fence = not in_fence
            continue
        if in_fence:
            out.append(line)
            continue
        if s == '$$':
            out.append(line)
            in_display = not in_display
            continue
        if in_display:
            # 展示公式：只规范运算符空格，不加反引号
            out.append(normalize_math(line))
            continue
        # 行内公式：$...$ -> $`...`$
        rebuilt, pos = [], 0
        for mobj in INLINE.finditer(line):
            rebuilt.append(line[pos:mobj.start()])
            rebuilt.append('$`' + normalize_math(mobj.group(1)) + '`$')
            pos = mobj.end()
            inline_count += 1
        rebuilt.append(line[pos:])
        out.append(''.join(rebuilt))
    return '\n'.join(out), inline_count


def main():
    root = Path(__file__).resolve().parent
    for md in sorted(root.glob('*.md')):
        raw = md.read_bytes()
        had_bom = raw.startswith(b'\xef\xbb\xbf')
        text = raw.decode('utf-8-sig')
        trailing_nl = text.endswith('\n')
        new_text, count = transform_text(text)
        if trailing_nl and not new_text.endswith('\n'):
            new_text += '\n'
        # UTF-8 无 BOM，LF 换行
        with md.open('wb') as f:
            f.write(new_text.encode('utf-8'))
        print(f'{md.name}: 行内公式 {count} 个, 去掉BOM={had_bom}')


if __name__ == '__main__':
    main()
