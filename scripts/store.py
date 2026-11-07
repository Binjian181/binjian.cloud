#!/usr/bin/env python3
"""文件型数据存储，替代 MySQL。

data/articles.jsonl  每行一篇完整的文章记录
data/seen_urls.txt   历史 URL 清单，只追加，用于抓取去重

写入时会按 KEEP_LIMIT 丢弃最旧的记录，让 articles.jsonl 体积稳定，
适合由 Actions 每次运行后提交回仓库。
"""
import json
import os

SITE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(SITE_DIR, 'data')
ARTICLES_FILE = os.path.join(DATA_DIR, 'articles.jsonl')
URLS_FILE = os.path.join(DATA_DIR, 'seen_urls.txt')

# 每类文章保留的上限，只需覆盖列表页展示窗口
KEEP_LIMIT = {'tech': 1500, 'people': 3000, 'original': 500}


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_articles():
    if not os.path.exists(ARTICLES_FILE):
        return []
    articles = []
    with open(ARTICLES_FILE, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                articles.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return articles


def save_articles(articles):
    """整体重写数据文件（先写临时文件再替换，避免中断留下半截文件）。"""
    _ensure_dir()
    tmp = ARTICLES_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        for a in articles:
            f.write(json.dumps(a, ensure_ascii=False) + '\n')
    os.replace(tmp, ARTICLES_FILE)


def load_seen_urls():
    if not os.path.exists(URLS_FILE):
        return set()
    with open(URLS_FILE, encoding='utf-8') as f:
        return {line.strip() for line in f if line.strip()}


def append_seen_urls(urls):
    _ensure_dir()
    with open(URLS_FILE, 'a', encoding='utf-8') as f:
        f.write('\n'.join(urls) + '\n')


def sort_key(a):
    """新→旧。SQL 里按 publish_time、score 排序，中文日期字符串同样适用。"""
    return (a.get('publish_time') or '', a.get('score') or 0, a.get('id') or 0)


def latest(articles, page_type, limit=1000):
    items = [a for a in articles if a.get('page_type') == page_type]
    items.sort(key=sort_key, reverse=True)
    return items[:limit]


def prune(articles):
    """按类型丢弃最旧的记录。"""
    kept = []
    for page_type, group in _group(articles):
        if page_type in KEEP_LIMIT:
            group.sort(key=sort_key, reverse=True)
            group = group[:KEEP_LIMIT[page_type]]
        kept.extend(group)
    kept.sort(key=lambda a: a.get('id') or 0)
    return kept


def _group(articles):
    groups = {}
    for a in articles:
        groups.setdefault(a.get('page_type') or '', []).append(a)
    return list(groups.items())


def normalize(record, page_type, record_id):
    return {
        'id': record_id,
        'title': (record.get('title') or '')[:500],
        'summary': record.get('summary') or '',
        'url': (record.get('url') or '').strip(),
        'source': record.get('source') or '',
        'publish_time': record.get('publish_time') or record.get('time') or '',
        'author': record.get('author') or '',
        'like_count': record.get('like_count') or 0,
        'comment_count': record.get('comment_count') or 0,
        'score': record.get('score') or 0,
        'page_type': page_type,
    }


def insert(records, page_type):
    """按 URL 去重后写入，返回新增数量。"""
    articles = load_articles()
    seen = load_seen_urls()
    current_id = max((a.get('id') or 0 for a in articles), default=0) + 1
    added = []
    for rec in records:
        url = (rec.get('url') or '').strip()
        if not url or url in seen:
            continue
        seen.add(url)
        added.append(normalize(rec, page_type, current_id))
        current_id += 1

    if added:
        append_seen_urls([a['url'] for a in added])
        save_articles(prune(articles + added))
    return len(added)


def url_exists(url):
    return (url or '').strip() in load_seen_urls()
