#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段 5.1：给全站 CSS 引用加缓存版本号 ?v=。

Nginx 对 css/js/图片设了 expires 1y + Cache-Control: public，
而全站页面的 /css/common.css 引用原本全部无版本号 —— 改完 CSS 老访客一年看不到。

覆盖：
  - 167 个页面：index.html / daily/*.html ×159 / article/*.html ×3
                / tech-news.html / people-news.html / articles.html / daily.html
  - 4 个源头模板：base.html / news_page.html / daily.html / daily_detail.html
                 （改这 4 处，未来新生成的页面自动带上版本号）
  - process_original_articles.py 的 ARTICLE_TEMPLATE

幂等：已带 ?v= 的不重复添加。
"""
import re
import sys
from pathlib import Path

SITE = Path('/var/www/binjian.cloud')
VER = '20260829'
WRITE = '--check' not in sys.argv

TARGETS = []
TARGETS.append(SITE / 'index.html')
TARGETS += sorted((SITE / 'daily').glob('*.html'))
TARGETS += sorted((SITE / 'article').glob('*.html'))
for name in ('tech-news.html', 'people-news.html', 'articles.html', 'daily.html'):
    TARGETS.append(SITE / name)
for rel in ('templates/base.html', 'templates/news_page.html',
            'templates/daily.html', 'templates/daily_detail.html',
            'templates/discussion_page.html'):
    TARGETS.append(SITE / rel)
TARGETS.append(Path('/home/ubuntu/process_original_articles.py'))

STRIP = re.compile(r'/css/common\.css\?v=[0-9]+')


def canonical(text):
    """把 /css/common.css 的引用统一成当前版本号（已有旧版本的先剥再加）。"""
    return STRIP.sub('/css/common.css', text).replace(
        '/css/common.css', '/css/common.css?v=' + VER)


def main():
    counts = {}
    todo, done, missing = [], [], []
    for p in TARGETS:
        if not p.exists():
            missing.append(p)
            continue
        t = p.read_text(encoding='utf-8')
        n = canonical(t)
        n_refs = n.count('/css/common.css?v=' + VER)
        counts[n_refs] = counts.get(n_refs, 0) + 1
        (todo if n != t else done).append((p, n))

    print('需更新：%d 个；已是当前版本号：%d 个；缺失：%d 个'
          % (len(todo), len(done), len(missing)))
    print('每个文件的 CSS 引用数分布：', counts)
    for p in missing:
        print('  ⚠️  不存在：', p)
    if done:
        print('  已是 v%s（跳过）：%s%s'
              % (VER, '、'.join(p.name for p, _ in done[:5]),
                 ' …' if len(done) > 5 else ''))
    if not WRITE:
        print('\n（--check 模式，未写入）')
        return
    for p, n in todo:
        p.write_text(n, encoding='utf-8')
    print('  ✅ 已更新 %d 个文件' % len(todo))


if __name__ == '__main__':
    main()
