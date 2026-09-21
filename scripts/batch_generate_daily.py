#!/usr/bin/env python3
"""
批量生成2026年1月1日后的文章精读页面
"""

import sys
import os
sys.path.insert(0, '/home/ubuntu')

from daily_people_article_push_v3 import (
    BailianAsyncAnalyzer, ParagraphAnalyzer,
    get_db_connection, get_and_clean_article,
    generate_web_page, regenerate_list_page,
    BASE_CONFIG, AI_CONFIG
)
import pymysql
from datetime import datetime, date
import json
import re
import time

# ==================== 配置区域 ====================

# 起始日期
START_DATE = '2026-01-01'

# 每次处理数量限制（0 表示不限制）
LIMIT = 0

# 每篇文章之间的间隔时间（秒），避免API频率限制
INTERVAL = 5

# ==================== 工具函数 ====================

def parse_publish_date(publish_time):
    """把 publish_time 解析成 date，无法解析时返回 None。

    库中 publish_time 是 varchar(50)，存的是「2026年08月28日 16:16」这类中文日期
    （有的不带时分，少数情况下也可能是 datetime 对象）。不能用 [:10] 按位截断：
    那只对月日零填充的写法成立，遇到「2026年1月5日」就会得到错误结果。
    """
    if isinstance(publish_time, datetime):
        return publish_time.date()

    text = str(publish_time or '')
    match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text)
    if match:
        year, month, day = match.groups()
        return date(int(year), int(month), int(day))

    match = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', text)
    if match:
        year, month, day = match.groups()
        return date(int(year), int(month), int(day))

    return None


# ==================== 主函数 ====================

def main():
    print("=" * 70)
    print(f"📖 批量生成文章精读页面")
    print(f"🕒 开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 筛选日期：{START_DATE} 之后")
    print("=" * 70)

    # 创建 AI 分析器
    ai_analyzer = BailianAsyncAnalyzer()
    analyzer = ParagraphAnalyzer(ai_analyzer)

    # 连接数据库
    conn = get_db_connection()

    try:
        with conn.cursor(cursor=pymysql.cursors.DictCursor) as cursor:
            sql = """
                SELECT id, title, url, source, publish_time 
                FROM news_articles 
                WHERE page_type = 'people' AND source = '人民网'
                AND title LIKE %s
                ORDER BY publish_time DESC
            """
            # 标题过滤与 daily_people_article_push_v3.py 保持一致（全角括号）
            cursor.execute(sql, ('%（人民时评）%',))
            articles = cursor.fetchall()

        # publish_time 是中文日期字符串，与 ISO 日期做字符串比较并不可靠
        # （此前 `publish_time >= '2026-01-01'` 只是碰巧成立），改为解析后再比较。
        start_date = datetime.strptime(START_DATE, '%Y-%m-%d').date()
        filtered = []
        for article in articles:
            publish_date = parse_publish_date(article['publish_time'])
            if publish_date is not None and publish_date >= start_date:
                filtered.append(article)
        articles = filtered

        print(f"\n✅ 找到 {len(articles)} 篇符合条件的文章\n")

        if len(articles) == 0:
            print("没有需要处理的文章")
            return

        # 获取已处理的URL
        list_file = os.path.join(BASE_CONFIG['output_dir'], 'daily', 'list.json')
        processed_urls = set()
        if os.path.exists(list_file):
            try:
                with open(list_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                    processed_urls = {a.get('original_url', '') for a in existing if a.get('original_url')}
            except Exception:
                pass

        # 过滤已处理的文章
        pending_articles = [a for a in articles if a['url'] not in processed_urls]
        print(f"📋 已处理 {len(articles) - len(pending_articles)} 篇，待处理 {len(pending_articles)} 篇\n")

        if LIMIT > 0:
            pending_articles = pending_articles[:LIMIT]
            print(f"⚠️  本次限制处理 {LIMIT} 篇\n")

        # 逐篇处理
        success_count = 0
        fail_count = 0

        for i, article in enumerate(pending_articles):
            print(f"\n{'='*60}")
            print(f"[{i+1}/{len(pending_articles)}] {article['title']}")
            print(f"{'='*60}")

            try:
                # 发布日期：统一解析，避免按位截断（原因见 parse_publish_date）
                parsed_date = parse_publish_date(article['publish_time'])
                if parsed_date is None:
                    print(f"⚠️  无法解析日期：{article['publish_time']!r}，跳过")
                    fail_count += 1
                    continue
                publish_date = parsed_date.strftime('%Y-%m-%d')
                display_date = parsed_date.strftime('%Y年%m月%d日')
                print(f"   时间：{display_date}")

                # 获取文章内容
                paragraphs, url = get_and_clean_article(article['url'])

                if not paragraphs:
                    print(f"⚠️  获取文章内容失败，跳过")
                    fail_count += 1
                    continue

                print(f"   📊 段落数：{len(paragraphs)}, 总字数：{sum(len(p) for p in paragraphs)}")

                # AI 分析
                if not analyzer.analyze_with_ai(article['title'], paragraphs):
                    print(f"❌ AI 分析失败，跳过")
                    fail_count += 1
                    continue

                # 生成网页
                generate_web_page(
                    article['title'],
                    paragraphs,
                    article['url'],
                    publish_date,
                    display_date,
                    analyzer,
                    analyzer.ai_result
                )

                # 重置 AI 结果，准备下一篇
                analyzer.ai_result = None
                success_count += 1

                print(f"✅ 处理完成")

                # 间隔等待
                if i < len(pending_articles) - 1:
                    time.sleep(INTERVAL)

            except Exception as e:
                print(f"❌ 处理失败：{e}")
                import traceback
                traceback.print_exc()
                fail_count += 1
                continue

        print("\n" + "=" * 70)
        print(f"✅ 批量处理完成！")
        print(f"   成功：{success_count} 篇")
        print(f"   失败：{fail_count} 篇")
        print(f"🌐 访问地址：https://binjian.cloud/daily.html")
        print("=" * 70)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
