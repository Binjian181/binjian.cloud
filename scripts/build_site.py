#!/usr/bin/env python3
"""把仓库组装成可直接发布的静态站点目录（供 GitHub Pages 使用）。

只复制浏览器需要访问的文件，源码、数据、模板、备份一律不进入发布目录。
"""
import os
import shutil
import sys

SITE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = os.environ.get('SITE_DOMAIN', 'binjian.cloud')

# 顶层目录白名单：出现在这里的目录才会被发布
INCLUDE_DIRS = {'css', 'js', 'img', 'images', 'fonts', 'icons',
                'article', 'daily', 'uploads', 'files'}

# 顶层文件：按后缀白名单，另外这几个文件始终发布
INCLUDE_SUFFIX = ('.html', '.png', '.jpg', '.jpeg', '.gif', '.svg',
                  '.ico', '.webmanifest')
INCLUDE_FILES = {'CNAME', '.nojekyll', 'favicon', 'robots.txt', 'sitemap.xml'}

# 缺少任何一个都说明生成步骤没跑全，宁可失败也不要把残缺站点推上去
REQUIRED_PAGES = ('index.html', 'tech-news.html', 'people-news.html',
                  'articles.html', 'daily.html')


def clean(dest):
    """清空发布目录里上一次的内容，保留 git 元数据。"""
    for name in os.listdir(dest):
        if name == '.git':
            continue
        path = os.path.join(dest, name)
        shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)


def build(dest):
    missing = [p for p in REQUIRED_PAGES
               if not os.path.isfile(os.path.join(SITE_DIR, p))]
    if missing:
        raise SystemExit(f"❌ 缺少必需页面，拒绝发布：{' '.join(missing)}")

    copied, skipped = [], []
    os.makedirs(dest, exist_ok=True)
    clean(dest)

    for name in sorted(os.listdir(SITE_DIR)):
        src = os.path.join(SITE_DIR, name)
        if os.path.isdir(src):
            if name not in INCLUDE_DIRS or not os.listdir(src):
                skipped.append(name + '/')
                continue
            shutil.copytree(src, os.path.join(dest, name), dirs_exist_ok=True)
            copied.append(name + '/')
        else:
            stem = os.path.splitext(name)[0]
            ok = name.endswith(INCLUDE_SUFFIX) or stem in INCLUDE_FILES
            if not ok:
                skipped.append(name)
                continue
            shutil.copy2(src, os.path.join(dest, name))
            copied.append(name)

    with open(os.path.join(dest, 'CNAME'), 'w') as f:
        f.write(DOMAIN + '\n')
    with open(os.path.join(dest, '.nojekyll'), 'w') as f:
        f.write('')

    return copied, skipped


if __name__ == '__main__':
    dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SITE_DIR, '.publish')
    copied, skipped = build(dest)
    print(f"✅ 发布目录已组装：{dest}")
    print(f"   收录 {len(copied)} 项：{' '.join(copied)}")
    print(f"   排除 {len(skipped)} 项：{' '.join(skipped)}")
