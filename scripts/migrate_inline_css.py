#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段 2：把 4 处内联 <style> 按作用域迁入 css/common.css。

原则：值一律照抄，只做选择器重写（加作用域前缀）与缩进规范化。
不做任何数值/颜色改动 —— 阶段 2 结束时渲染结果必须与迁移前逐像素一致。

输出：/tmp/migrated_{home,daily,article,discussion}.css
"""
import re
import sys

SITE = '/var/www/binjian.cloud'
TOPBAR_TOKEN = 'var(--topbar-h)'


# ---------------------------------------------------------------- 作用域映射
def _sel(cond, prefix, sel):
    """条件成立则给选择器加作用域前缀，否则原样返回。"""
    return prefix + sel if cond and not sel.startswith(prefix) else sel


def map_daily(sel):
    if sel.startswith(('.main-content', '.article-container')):
        return sel  # 幂等
    if re.fullmatch(r'\.back-link|\.article-header', sel):
        return '.main-content > ' + sel
    if re.fullmatch(r'\.article-title|\.article-meta|\.article-meta a|\.article-meta a:hover', sel):
        return '.main-content ' + sel
    return sel


def map_article(sel):
    if sel.startswith(('.article-container', '.main-content')):
        return sel
    if re.fullmatch(r'\.back-link|\.article-header|\.article-title|\.article-meta', sel):
        return '.article-container > ' + sel if sel in ('.back-link', '.article-header') \
            else '.article-container ' + sel
    return sel


# ---------------------------------------------------------------- CSS 解析
def strip_outer(css, depth=0):
    """剥掉最外一层花括号，返回内部文本。"""
    start = css.index('{', 0)
    i, level = start, 0
    while i < len(css):
        if css[i] == '{':
            level += 1
        elif css[i] == '}':
            level -= 1
            if level == 0:
                return css[start + 1:i]
        i += 1
    raise ValueError('括号不配对')


def split_top(css):
    """把 CSS 文本切成 ('rule', header, body) / ('atrule', header, body)。"""
    out, i = [], 0
    while i < len(css):
        m = re.compile(r'(?:/\*.*?\*/|"[^"]*"|\s)+', re.S).match(css, i)
        if m:
            i = m.end()
            continue
        j = css.index('{', i)
        header = css[i:j].strip()
        k, level = j, 0
        while k < len(css):
            if css[k] == '{':
                level += 1
            elif css[k] == '}':
                level -= 1
                if level == 0:
                    break
            k += 1
        body = strip_outer(css[j:k + 1])
        out.append(('atrule' if header.startswith('@') else 'rule', header, body))
        i = k + 1
    return out


def split_decls(body):
    """按分号切声明；容错处理值内含分号（如 content: ';'）。"""
    out = []
    for frag in body.split(';'):
        frag = frag.strip()
        if not frag:
            continue
        if out and ':' not in frag.split('\n')[0]:
            out[-1] += ';' + frag          # 上一个声明的值被误切，接回去
        else:
            out.append(frag)
    return out


def transform(css, mapper, topbar=False):
    """递归转换：规则加作用域前缀，at-rule 递归处理内部。输出无整体缩进。"""
    out = []
    for kind, header, body in split_top(css):
        if kind == 'rule':
            if header.startswith(('.main-content', '.article-container')):
                parts = [p.strip() for p in header.split(',')]
            else:
                parts = [mapper(p.strip()) for p in header.split(',')]
            decls = ['    ' + d.strip() + ';' for d in split_decls(body)]
            sel = ', '.join(parts)
            if len(sel) > 76:
                sel = ',\n'.join(parts)
            out.append(sel + ' {\n' + '\n'.join(decls) + '\n}')
        else:
            inner = re.sub(r'\n{3,}', '\n\n', transform(body, mapper, topbar))
            inner = '\n'.join(('    ' + ln if ln.strip() else '') for ln in inner.split('\n'))
            out.append(header + ' {\n' + inner + '\n}')
    text = '\n\n'.join(out)
    if topbar:
        text = text.replace('top: 60px', 'top: ' + TOPBAR_TOKEN)
    return text


# ---------------------------------------------------------------- 提取内联块
def extract_style(text, label):
    m = re.search(r'^([ \t]*)<style>(.*?)^[ \t]*</style>', text, re.S | re.M)
    if not m:
        sys.exit('未找到 <style> 块：' + label)
    return m.group(2)


def main():
    # 1. 首页
    idx = open(SITE + '/index.html', encoding='utf-8').read()
    homecss = extract_style(idx, 'index.html')

    # 2. daily 详情模板
    dd = open(SITE + '/templates/daily_detail.html', encoding='utf-8').read()
    dailycss = extract_style(dd, 'daily_detail.html')

    # 3. 原创文章模板（Python str.format —— 花括号双写，需反转义）
    py = open('/home/ubuntu/process_original_articles.py', encoding='utf-8').read()
    artcss = extract_style(py, 'process_original_articles.py')
    artcss = artcss.replace('{{', '{').replace('}}', '}')

    # 4. 讨论区（死模板）
    disc = open(SITE + '/templates/discussion_page.html', encoding='utf-8').read()
    disccss = extract_style(disc, 'discussion_page.html')

    blocks = {
        'home': transform(homecss, lambda s: s, topbar=True),
        'daily': transform(dailycss, map_daily),
        'article': transform(artcss, map_article),
        'discussion': transform(disccss, lambda s: s),
    }
    for name, text in blocks.items():
        path = '/tmp/migrated_%s.css' % name
        open(path, 'w', encoding='utf-8').write(text + '\n')
        print('%s: %d 行 -> %s' % (name, text.count('\n') + 1, path))


if __name__ == '__main__':
    main()
