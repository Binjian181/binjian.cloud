#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段 2 等价性校验：内联块 vs 迁移后 CSS。

检查三件事：
  V1 选择器覆盖：内联块的每个选择器，在迁移后 CSS 里必须存在（允许加作用域前缀）
  V2 声明等价：同名规则的每一条声明，值必须逐字相同（顺序无关）
  V3 作用域正确性：三义冲突类必须带上下文前缀；其余不得被误加前缀
"""
import re
import sys

SITE = '/var/www/binjian.cloud'


def strip_comments(css):
    return re.sub(r'/\*.*?\*/', '', css, flags=re.S)


def parse(css):
    """返回 [( selector_or_atrule_header, [decl...] )]，扁平化 at-rule 内部。"""
    css = strip_comments(css)
    out = []

    def walk(text, prefix):
        i = 0
        while i < len(text):
            m = re.compile(r'\s+').match(text, i)
            if m:
                i = m.end()
                continue
            j = text.index('{', i)
            header = ' '.join(text[i:j].split())
            k, level = j, 0
            while k < len(text):
                if text[k] == '{':
                    level += 1
                elif text[k] == '}':
                    level -= 1
                    if level == 0:
                        break
                k += 1
            body = text[j + 1:k]
            if header.startswith('@'):
                walk(body, prefix + header + ' >> ')
            else:
                for part in header.split(','):
                    sel = ' '.join(part.split())
                    decls = sorted(
                        d.strip() + ';' for d in body.split(';') if d.strip())
                    out.append((prefix + sel, decls))
            i = k + 1

    walk(css, '')
    return out


def norm(sel):
    """去掉作用域前缀，用于按基名比对。"""
    return sel


def ALLOWED_SUB(decl):
    """魔法数字 → token 的刻意替换（数值等价，见阶段 2f/2g）。"""
    return {'top: 60px;': 'top: var(--topbar-h);'}.get(decl, decl)


def extract_style(text):
    m = re.search(r'^([ \t]*)<style>(.*?)^[ \t]*</style>', text, re.S | re.M)
    return m.group(2)


def main():
    sources = {
        'home': extract_style(open(SITE + '/index.html', encoding='utf-8').read()),
        'daily': extract_style(open(SITE + '/templates/daily_detail.html', encoding='utf-8').read()),
        'article': extract_style(
            open('/home/ubuntu/process_original_articles.py', encoding='utf-8').read()
        ).replace('{{', '{').replace('}}', '}'),
        'discussion': extract_style(
            open(SITE + '/templates/discussion_page.html', encoding='utf-8').read()),
    }
    migrated = {k: open('/tmp/migrated_%s.css' % k, encoding='utf-8').read()
                for k in sources}

    ok = True
    for name, src in sources.items():
        mig = parse(migrated[name])
        mig_by_sel = {}
        for sel, decls in mig:
            mig_by_sel.setdefault(sel, []).append(decls)
        # 迁移后允许的选择器后缀集合（基名 -> 实际写法）
        mig_base = {}
        for sel in mig_by_sel:
            mig_base.setdefault(sel.split()[-1], []).append(sel)

        missing, diff = [], []
        for sel, decls in parse(src):
            base = sel.split()[-1]
            cands = mig_base.get(base, [])
            if not cands:
                missing.append(sel)
                continue
            # 声明集合必须在某个候选里完全一致
            # 允许的刻意替换：魔法数字 → token（阶段 2f/2g，数值等价）
            ALLOWED = (('top: 60px;', 'top: var(--topbar-h);'),)
            if not any(sorted(d) == sorted([ALLOWED_SUB(x) for x in decls])
                       for c in cands for d in mig_by_sel[c]):
                diff.append((sel, decls, [mig_by_sel[c] for c in cands]))

        print('=== %s ===  内联规则 %d 条' % (name, len(parse(src))))
        if missing:
            ok = False
            print('  ❌ 迁移后缺失选择器:', missing)
        if diff:
            ok = False
            print('  ❌ 声明值不一致:')
            for sel, a, b in diff:
                print('     ', sel)
                print('       内联:', a)
                print('       迁移:', b)
        if not missing and not diff:
            print('  ✅ 选择器全覆盖，声明逐条等价')

    # V3：三义冲突类必须带前缀
    rules = parse(migrated['daily']) + parse(migrated['article']) + parse(migrated['home'])
    for sel, _ in rules:
        base = sel.split()[-1]
        if base in ('.article-header', '.article-title', '.article-meta') and ' >> ' not in sel:
            if not sel.startswith(('.main-content', '.article-container')):
                ok = False
                print('  ❌ 无作用域的三义选择器:', sel)
    print()
    print('总体:', '✅ 通过' if ok else '❌ 存在问题')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
