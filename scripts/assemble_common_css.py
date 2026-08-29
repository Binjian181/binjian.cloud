#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段 2 组装：把 /tmp/migrated_*.css 并入 css/common.css。

策略（保证全站每个断点只有一份媒体块）：
  1. 先把迁移后 CSS 里的顶层 @media 块**摘出来**，剩下的普通规则插入「内联样式回收区」
  2. 摘出的媒体规则合并进文件末尾的响应式区（1024 / 768 / 390）
  3. 390 断点单独处理：因新增了 .home-container 顶层规则，必须排在其后

幂等保护：检测到插入标记则拒绝写入。锚点缺失也拒绝写入（绝不静默失败）。
"""
import re
import sys

PATH = '/var/www/binjian.cloud/css/common.css'
MARK_INSERT = '内联样式回收区'
RESP = '/* ========== 响应式设计 ========== */'

css = open(PATH, encoding='utf-8').read()
if MARK_INSERT in css:
    sys.exit('拒绝写入：已存在插入标记，说明本脚本已运行过（如需重来：git checkout -- css/common.css）')

home = open('/tmp/migrated_home.css', encoding='utf-8').read().strip()
daily = open('/tmp/migrated_daily.css', encoding='utf-8').read().strip()
article = open('/tmp/migrated_article.css', encoding='utf-8').read().strip()
discussion = open('/tmp/migrated_discussion.css', encoding='utf-8').read().strip()


def block_at(text, header, after=None):
    """取出某个 @media 块的内部文本。after：只在指定标记之后搜索。"""
    base = text.index(after) if after else 0
    i = text.index(header, base)
    j = text.index('{', i)
    k, level = j, 0
    while k < len(text):
        if text[k] == '{':
            level += 1
        elif text[k] == '}':
            level -= 1
            if level == 0:
                break
        k += 1
    return text[j + 1:k], i, k + 1


def split_media(css_text):
    """把顶层 @media 块从 CSS 中摘出，返回 (剩余普通规则, {header: 内部文本})。"""
    media, i = {}, 0
    while True:
        m = re.compile(r'@media[^{]*\{').search(css_text, i)
        if not m:
            break
        start = m.start()
        k, level = m.end() - 1, 0
        while k < len(css_text):
            if css_text[k] == '{':
                level += 1
            elif css_text[k] == '}':
                level -= 1
                if level == 0:
                    break
            k += 1
        header = ' '.join(m.group(0)[:-1].split())
        media.setdefault(header, []).append(css_text[m.end():k].strip())
        css_text = css_text[:start] + css_text[k + 1:]
        i = start
    return re.sub(r'\n{3,}', '\n\n', css_text).strip(), {k: '\n\n'.join(v) for k, v in media.items()}


def reindent(text, pad='    '):
    return '\n'.join((pad + ln if ln.strip() else '') for ln in text.split('\n'))


# ---------------------------------------------------------------- 1. 拆分媒体块
blocks = {}
rest = {}
for name, text in (('home', home), ('daily', daily), ('article', article), ('discussion', discussion)):
    r, m = split_media(text)
    rest[name] = r
    blocks[name] = m

# ---------------------------------------------------------------- 2. 插入回收区
header_block = """/* ========== 内联样式回收区 ========== */
/* 本区内容原先以内联 <style> 分散在 4 处（index.html / templates/daily_detail.html /
   process_original_articles.py 的 ARTICLE_TEMPLATE / templates/discussion_page.html）。
   值一律照抄，仅重写选择器作用域 —— 三义冲突类（.article-header/.article-title/.article-meta）
   按上下文加前缀：daily 详情 .main-content、原创详情 .article-container。
   各断点规则不在此处，统一并入文件末尾响应式区。阶段 2 前后面貌逐像素等价。 */

"""

sections = [
    ('/* ---- 回收：index.html 首页 ---- */\n\n', 'home'),
    ('/* ---- 回收：templates/daily_detail.html 时评精读详情 ---- */\n\n', 'daily'),
    ('/* ---- 回收：process_original_articles.py 原创文章详情 ---- */\n\n', 'article'),
    ('/* ---- 回收：templates/discussion_page.html 讨论区（死模板，功能预留） ---- */\n\n', 'discussion'),
]
body = header_block + '\n\n'.join(h + rest[n] for h, n in sections) + '\n\n'

if css.count(RESP) != 1:
    sys.exit('锚点 %r 出现 %d 次，拒绝写入' % (RESP, css.count(RESP)))
css = css.replace(RESP, body + RESP, 1)

# ---------------------------------------------------------------- 3. 合并媒体块
# 3a. 1024：并入首页两列规则；抽屉 top 改用 --topbar-h
inner, i, j = block_at(css, '@media (max-width: 1024px)', after=RESP)
merged = inner.rstrip() + '\n\n' + reindent(blocks['home'].get('@media (max-width: 1024px)', ''))
merged = re.sub(r'\n{3,}', '\n\n', merged).rstrip() + '\n'
merged = merged.replace('top: 60px', 'top: var(--topbar-h)')
css = css[:i] + '@media (max-width: 1024px) {' + merged + '}' + css[j:]

# 3b. 768：并入首页 / daily / article 三处
inner, i, j = block_at(css, '@media (max-width: 768px)', after=RESP)
added = [blocks[n].get('@media (max-width: 768px)') for n in ('home', 'daily', 'article')]
merged = inner.rstrip() + '\n\n' + '\n\n'.join(reindent(t) for t in added if t)
merged = re.sub(r'\n{3,}', '\n\n', merged).rstrip() + '\n'
css = css[:i] + '@media (max-width: 768px) {' + merged + '}' + css[j:]

# 3c. 390：回收区里的 390 块已摘出；此处摘出原 390 块内 .home-container 规则，
#     改放到整个响应式区之后 —— 同为 0,1,0 特异性，必须排在 .home-container 顶层规则之后
inner, i, j = block_at(css, '@media (max-width: 390px)', after=RESP)
m = re.search(r'\n    \.home-container \{\n(?:.*?\n)*?    \}\n', inner)
if not m:
    sys.exit('未在 390 块中找到 .home-container 规则，拒绝写入')
rule390 = m.group(0)
css = css[:i] + '@media (max-width: 390px) {' + inner.replace(rule390, '\n', 1).rstrip() + '\n}' + css[j:]

anchor = '/* ========== 底部备案信息 ========== */'
if css.count(anchor) != 1:
    sys.exit('页脚锚点异常，拒绝写入')
new390 = ('@media (max-width: 390px) {\n'
          '    /* 必须排在 .home-container 顶层规则之后：同为 0,1,0 特异性，靠源码顺序取胜 */\n'
          '    .home-container {\n        padding: 0 14px;\n    }\n}\n\n')
css = css.replace(anchor, new390 + anchor, 1)

open(PATH, 'w', encoding='utf-8').write(css)
print('写入完成，行数：', css.count('\n') + 1)
