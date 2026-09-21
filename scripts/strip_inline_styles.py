#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段 3：剥离全部内联 <style>，并给 CSS 引用加缓存版本号 ?v=。

安全策略（校验优先、遇错即停）：
  - 用标记匹配定位 <style> 与 </style>，绝不使用固定行号
  - 每个文件只允许出现一对 <style>/</style>；块内容需符合预期（可传 md5 校验）
  - 先做全量「预检」，全部通过后才真正写入
  - 写入前自动备份到 /tmp/strip_backup/

用法：
  python3 strip_inline_styles.py --check     # 只预检，不写入
  python3 strip_inline_styles.py             # 预检通过后写入
"""
import hashlib
import re
import shutil
import sys
from pathlib import Path

SITE = Path('/var/www/binjian.cloud')
VER = '20260829'
BACKUP = Path('/tmp/strip_backup')
WRITE = '--check' not in sys.argv

# 159 篇 daily 页的内联块内容必须全等，但不对 md5 取值做硬编码假设
# （口径依赖提取方式）。预检阶段动态算出全部取值，确认唯一后再写入。
DAILY_MD5 = None

STYLE_RE = re.compile(r'^[ \t]*<style>(?:(?!</style>).)*</style>\n?', re.S | re.M)


def find_blocks(text):
    return [(m.start(), m.end(), m.group(0)) for m in STYLE_RE.finditer(text)]


def check(path, expect_md5=None):
    """返回 (状态, md5, 说明)。状态：'ok' 可剥离 / 'done' 已剥离 / 'bad' 有问题。"""
    text = path.read_text(encoding='utf-8')
    blocks = find_blocks(text)
    if not blocks:
        # 幂等：已剥离过的文件不算失败，但要求 CSS 引用带版本号，以防上次只剥了一半
        if 'common.css?v=' in text:
            return 'done', '', '已剥离（CSS 已带版本号）'
        return 'bad', '', '无内联 <style> 且 CSS 无版本号 —— 状态可疑，需人工确认'
    if len(blocks) > 1:
        return False, '', '出现 %d 个 <style> 块，拒绝自动处理' % len(blocks)
    body = re.search(r'<style>(.*)</style>', blocks[0][2], re.S).group(1)
    md5 = hashlib.md5(body.encode()).hexdigest()
    info = '行数 %d，md5 %s' % (body.count('\n') + 1, md5[:8])
    if expect_md5 and md5 != expect_md5:
        return 'bad', md5, 'md5 不符（期望 %s，实际 %s）' % (expect_md5[:8], md5)
    return 'ok', md5, info


def strip_file(path, expect_md5=None):
    state, _md5, info = check(path, expect_md5)
    if state != 'ok':
        return False, info
    text = path.read_text(encoding='utf-8')
    new = STYLE_RE.sub('', text, count=1)
    if WRITE:
        dest = BACKUP / path.name
        shutil.copy2(path, dest)
        path.write_text(new, encoding='utf-8')
    return True, info


def strip_py_template(path):
    """process_original_articles.py 的 ARTICLE_TEMPLATE 是 str.format 模板，
    块内花括号双写，故用非贪婪匹配到第一个 </style> 即可（已确认无嵌套）。"""
    text = path.read_text(encoding='utf-8')
    i = text.index('ARTICLE_TEMPLATE')
    m = re.search(r'[ \t]*<style>(?:(?!</style>).)*</style>\n?', text[i:], re.S | re.M)
    if not m:
        return False, 'ARTICLE_TEMPLATE 内未找到 <style> 块'
    body = m.group(0)
    info = '行数 %d，md5 %s' % (
        body.count('\n'), hashlib.md5(body.encode()).hexdigest()[:8])
    if not WRITE:
        return True, info
    new = text.replace(body, '', 1)
    dest = BACKUP / path.name
    shutil.copy2(path, dest)
    path.write_text(new, encoding='utf-8')
    return True, info


def main():
    if WRITE:
        BACKUP.mkdir(parents=True, exist_ok=True)

    # (显示名, 路径, 分组)  分组：None=不校验 md5，'daily'=校验唯一取值，'article'=不校验
    jobs = []
    jobs.append(('index.html', SITE / 'index.html', None))
    jobs.append(('templates/daily_detail.html',
                 SITE / 'templates/daily_detail.html', None))
    for f in sorted((SITE / 'daily').glob('*.html')):
        jobs.append(('daily/' + f.name, f, 'daily'))
    for f in sorted((SITE / 'article').glob('*.html')):
        jobs.append(('article/' + f.name, f, None))

    print('预检 %d 个文件：' % len(jobs))
    bad, already = [], []
    for name, path, _group in jobs:
        state, _md5, info = check(path, None)   # 预检阶段不校验 md5（取值在下面动态算出）
        if state == 'bad':
            bad.append((name, info))
            print('  ❌ %-40s %s' % (name, info))
        elif state == 'done':
            already.append(name)
    if bad:
        sys.exit('\n预检未通过（%d 个），未写入任何文件' % len(bad))
    print('  ✅ 全部通过，每个待处理文件恰好一对 <style>/</style>')
    if already:
        print('  ⏭️  已剥离跳过 %d 个：%s%s'
              % (len(already), '、'.join(already[:4]),
                 ' …' if len(already) > 4 else ''))
    dm = {check(p, None)[1] for _, p, g in jobs if g == 'daily'}
    print('  daily 内联块 md5 取值集合（%d 篇）：' % len(dm), {x[:8] for x in dm})
    if len(dm) != 1:
        sys.exit('\ndaily 页的内联块内容不全等（%d 种），拒绝批量处理' % len(dm))
    am = {check(p, None)[1] for n, p, _ in jobs if n.startswith('article/')}
    print('  article 内联块 md5 取值集合：', {x[:8] for x in am})

    # 把算出的 daily md5 作为写入时的硬校验
    daily_md5 = dm.pop()
    jobs = [(n, p, daily_md5 if g == 'daily' else None) for n, p, g in jobs]

    if not WRITE:
        print('\n（--check 模式，未写入）')
        return

    for name, path, md5 in jobs:
        ok, info = strip_file(path, md5)
        print('  %s %-40s %s' % ('✅' if ok else '❌', name, info))

    ok, info = strip_py_template(Path('/home/ubuntu/process_original_articles.py'))
    print('  %s %-40s %s' % ('✅' if ok else '❌',
                             'process_original_articles.py', info))

    # discussion_page.html：清空 extra_css 块（样式已在阶段 2d 迁入 common.css）
    disc = SITE / 'templates/discussion_page.html'
    text = disc.read_text(encoding='utf-8')
    new = re.sub(r'\{% block extra_css %\}.*?\{% endblock %\}\n?', '',
                 text, flags=re.S)
    if new != text:
        shutil.copy2(disc, BACKUP / 'discussion_page.html')
        disc.write_text(new, encoding='utf-8')
        print('  ✅ %-40s 清空 extra_css 块' % 'templates/discussion_page.html')

    print('\n备份目录：', BACKUP)
    print('注：缓存版本号 ?v= 由 add_cache_version.py 单独处理（覆盖全部 167 个页面）')


if __name__ == '__main__':
    main()
