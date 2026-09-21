#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CSS 空白规范化：重排缩进为 4 空格、压缩多余空行。

模型：先按行拼成逻辑行（以 '{' / '}' / ';' 结尾），再按花括号深度输出缩进。
只动空白与换行，不改任何内容（选择器 / 属性 / 值 / 顺序一律不变）。

安全护栏：规范化前后去掉全部空白后必须逐字符相同，且花括号平衡，否则拒绝写入。
"""
import re
import sys

PATH = '/var/www/binjian.cloud/css/common.css'
if len(sys.argv) > 1:
    PATH = sys.argv[1]


def format_css(src):
    out, buf, depth, prev = [], '', 0, None

    def flush():
        nonlocal buf
        buf = buf.strip()
        if not buf:
            return
        # 形如 `*/ --x: 1;`（多行注释的收尾与下一条声明挤在同一行）拆成两行
        m = re.match(r'^(\*/)\s*(\S.*)$', buf)
        if m:
            emit(m.group(1))
            buf = m.group(2)
            return
        emit(buf)
        buf = ''

    def emit(piece):
        nonlocal depth, prev
        if piece.endswith('{'):
            indented = '    ' * depth + piece
            depth += 1
        elif piece.endswith('}'):
            depth -= 1
            indented = '    ' * depth + piece
        else:
            indented = '    ' * depth + piece
        # 规则之间空一行：上一条以 } 结束（规则或块），当前不是块的收尾
        if prev is not None and prev.endswith('}') and piece != '}':
            out.append('')
        out.append(indented)
        prev = piece

    for raw in src.split('\n'):
        line = raw.strip()
        if not line:
            continue
        # 注释 / at-rule 永远自己起一行：拼接前先把已有内容冲出
        # 例外：buf 以 ':' 结尾（形如 `--tier-highest:` 后跟行尾注释），值是下一行，不能冲
        if not buf.endswith(':') and (line.startswith(('/*', '@')) or buf.startswith(('/*', '@'))):
            flush()
        buf += (' ' if buf else '') + line
        while True:
            m = re.search(r'[{};]', buf)
            if not m:
                break
            piece, buf = buf[:m.end()].strip(), buf[m.end():].strip()
            if piece:
                emit(piece)
            # 注释 / at-rule 若跟在同一行后面，先结束当前逻辑行
            if buf.startswith(('/*', '@')):
                flush()

    if buf.strip():
        emit(buf.strip())

    return '\n'.join(out).strip() + '\n'


def main():
    src = open(PATH, encoding='utf-8').read()
    dst = format_css(src)

    squash = lambda s: re.sub(r'\s+', '', s)
    if squash(src) != squash(dst):
        sys.exit('护栏失败：规范化前后内容不一致，拒绝写入')
    nocom = re.sub(r'/\*.*?\*/', '', dst, flags=re.S)
    if nocom.count('{') != nocom.count('}'):
        sys.exit('护栏失败：花括号不平衡，拒绝写入')

    if src == dst:
        print('无需改动')
        return
    open(PATH, 'w', encoding='utf-8').write(dst)
    print('%s: %d 行 -> %d 行' % (PATH, src.count('\n') + 1, dst.count('\n') + 1))


if __name__ == '__main__':
    main()
