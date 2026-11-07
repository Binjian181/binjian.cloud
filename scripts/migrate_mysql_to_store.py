#!/usr/bin/env python3
"""一次性迁移工具：把本地 MySQL 的 news_articles 导出为文件型数据。

运行一次即可，Actions 流水线不再依赖 MySQL。
"""
import os
import json
import sys

import pymysql

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.path.dirname(SCRIPTS_DIR)
sys.path.insert(0, SCRIPTS_DIR)
import store

DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': os.environ.get('ARTICLES_DB_PASSWORD', ''),
    'database': 'articles',
    'charset': 'utf8mb4',
}


def main():
    conn = pymysql.connect(**DB_CONFIG)
    with conn.cursor(cursor=pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT * FROM news_articles ORDER BY id")
        rows = cursor.fetchall()
    conn.close()

    records = [store.normalize({k: ('' if v is None else v) for k, v in row.items()},
                              row.get('page_type') or 'tech', row['id'])
               for row in rows]
    urls = [r['url'] for r in records if r['url']]

    store.save_articles(store.prune(records))
    os.makedirs(store.DATA_DIR, exist_ok=True)
    with open(store.URLS_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(urls) + '\n')

    kept = store.load_articles()
    counts = {}
    for row in kept:
        counts[row['page_type']] = counts.get(row['page_type'], 0) + 1
    print(f"✅ 导出 {len(records)} 条，裁剪后保留 {len(kept)} 条：{counts}")
    print(f"   {store.ARTICLES_FILE}")
    print(f"   {store.URLS_FILE}（{len(set(urls))} 个 URL）")


if __name__ == '__main__':
    main()
