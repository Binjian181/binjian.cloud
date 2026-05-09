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
from datetime import datetime
import json
import time

# ==================== 配置区域 ====================

# 起始日期
START_DATE = '2026-01-01'

# 每次处理数量限制（0 表示不限制）
LIMIT = 0

# 每篇文章之间的间隔时间（秒），避免API频率限制
INTERVAL = 5

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
                AND title LIKE '%%人民时评%%'
                AND publish_time >= '{}'
                ORDER BY publish_time DESC
            """.format(START_DATE)
            cursor.execute(sql)
            articles = cursor.fetchall()

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
            except:
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
                # 格式化日期
                publish_time = article['publish_time']
                if isinstance(publish_time, datetime):
                    publish_date = publish_time.strftime('%Y-%m-%d')
                else:
                    date_str = str(publish_time)[:10]
                    if '年' in date_str:
                        date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
                    publish_date = date_str

                display_date = publish_date.replace('-', '年', 1).replace('-', '月', 1) + '日'
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
