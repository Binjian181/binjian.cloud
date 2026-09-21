#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻爬虫脚本 - 爬取科技资讯和时政观点并存入数据库
数据源：
  - 科技资讯：少数派、36氪、澎湃新闻科技频道
  - 时政观点：人民网观点频道
定时任务：每 3 小时执行一次
crontab: 0 */3 * * * cd /home/ubuntu && python3 fetch_news.py >> /home/ubuntu/fetch_news.log 2>&1
"""

import requests
from bs4 import BeautifulSoup
import datetime
import json
from urllib.parse import urljoin
import time
import re
import pymysql
from urllib3.exceptions import InsecureRequestWarning

# 禁用 SSL 警告
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '19930107ZBj',
    'database': 'articles',
    'charset': 'utf8mb4'
}

# 配置
MAX_ARTICLES_PER_SOURCE = 50  # 每个来源最多爬取的文章数


def clean_summary(text):
    """清理摘要：去除URL、Markdown图片语法、过长英文串，防止移动端页面溢出"""
    if not text:
        return text
    # 去除 Markdown 图片语法 ![alt](url)
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    # 去除 URL
    text = re.sub(r'https?://\S+', '', text)
    # 去除 @username 引用
    text = re.sub(r'@\w+', '', text)
    # 在日期后插入空格（如 "2026-04-17By" -> "2026-04-17 By"）
    text = re.sub(r'(\d{4}-\d{2}-\d{2})([A-Za-z])', r'\1 \2', text)
    # 在数字+大写字母开头单词之间加空格
    text = re.sub(r'(\d)([A-Z][a-z])', r'\1 \2', text)
    # 清理多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def get_db_connection():
    """获取数据库连接"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"数据库连接失败：{e}")
        return None


def save_to_database(articles, page_type):
    """保存文章到数据库"""
    conn = get_db_connection()
    if not conn:
        return 0
    
    try:
        cursor = conn.cursor()
        
        # 去重：检查已存在的 URL
        existing_urls = set()
        for article in articles:
            if article['url']:
                existing_urls.add(article['url'])
        
        if existing_urls:
            placeholders = ','.join(['%s'] * len(existing_urls))
            cursor.execute(f"SELECT url FROM news_articles WHERE url IN ({placeholders})", list(existing_urls))
            existing_urls = {row[0] for row in cursor.fetchall()}
        
        # 插入新文章
        count = 0
        for article in articles:
            if article['url'] in existing_urls:
                continue
            
            sql = """
            INSERT INTO news_articles 
            (title, summary, url, source, publish_time, author, like_count, comment_count, score, page_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(sql, (
                article.get('title', '')[:500],
                clean_summary(article.get('summary', '')),
                article.get('url', ''),
                article.get('source', ''),
                article.get('time', ''),
                article.get('author', ''),
                article.get('like_count', 0),
                article.get('comment_count', 0),
                article.get('score', 0),
                page_type
            ))
            count += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return count
    except Exception as e:
        print(f"保存数据失败：{e}")
        conn.rollback()
        return 0


# 爬取少数派最新文章
def fetch_sspai():
    """爬取少数派文章"""
    articles = []
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }
        
        response = requests.get(
            "https://sspai.com/api/v1/articles?offset=0&limit=30&sort=created_at&include=tags,author",
            headers=headers,
            timeout=15,
            verify=False
        )
        
        if response.status_code == 200:
            data = response.json()
            for item in data.get("list", []):
                score = 70 + item.get("like_count", 0) // 10 + item.get("comment_count", 0) // 5
                
                articles.append({
                    "title": item.get("title", ""),
                    "summary": item.get("summary", "")[:500],
                    "url": f"https://sspai.com/post/{item.get('id', '')}",
                    "source": "少数派",
                    "time": datetime.datetime.fromtimestamp(item.get("created_at", 0)).strftime("%Y-%m-%d %H:%M"),
                    "score": score,
                    "author": item.get("author", {}).get("nickname", ""),
                    "like_count": item.get("like_count", 0),
                    "comment_count": item.get("comment_count", 0)
                })
                
                if len(articles) >= MAX_ARTICLES_PER_SOURCE:
                    break
                    
    except Exception as e:
        print(f"爬取少数派失败：{e}")
    
    print(f"✅ 爬取到 {len(articles)} 篇少数派文章")
    return articles


# 36 氪官方接口（36kr.com 自 2026-08 起全站启用 JS 反爬挑战，HTML/RSS 一律返回验证页）
KR_GATEWAY = "https://gateway.36kr.com/api/mis/nav"
KR_SUBNAV_FLOW = KR_GATEWAY + "/ifm/subNav/flow"       # 栏目文章流
KR_NEWSFLASH_FLOW = KR_GATEWAY + "/newsflash/flow"     # 快讯流
# 36 氪信息流下的栏目 nick，web_news 为科技频道
KR_SUBNAV_NICKS = ["web_news"]
KR_PAGE_SIZE = 30
KR_MAX_PAGES = 3
# 两个流的配额之和为 MAX_ARTICLES_PER_SOURCE，避免文章把快讯全部挤掉
KR_ARTICLE_QUOTA = 40
KR_NEWSFLASH_QUOTA = MAX_ARTICLES_PER_SOURCE - KR_ARTICLE_QUOTA


def _kr_post(url, param, timeout=15):
    """调用 36 氪网关接口。注意：首屏 pageEvent=0（传 1 会报「请求分页回调值不能为空」）"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": "https://36kr.com",
        "Referer": "https://36kr.com/",
    }
    payload = {"partner_id": "wap", "timestamp": 0, "param": param}
    resp = requests.post(
        url,
        headers=headers,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        timeout=timeout,
        verify=False
    )
    body = resp.json()
    if body.get("code") != 0:
        raise RuntimeError(body.get("msg") or f"code={body.get('code')}")
    return body.get("data") or {}


def _kr_fetch_items(url, base_param, max_items):
    """按分页拉取条目，返回原始 item 列表"""
    items = []
    callback = ""
    for page in range(KR_MAX_PAGES):
        param = dict(base_param)
        param["pageSize"] = KR_PAGE_SIZE
        param["pageEvent"] = 0 if page == 0 else 1
        param["pageCallback"] = callback

        try:
            data = _kr_post(url, param)
        except Exception as e:
            print(f"36 氪接口请求失败（第 {page + 1} 页）：{e}")
            break

        batch = data.get("itemList") or []
        if not batch:
            break

        items.extend(batch)
        callback = data.get("pageCallback") or ""
        if not data.get("hasNextPage") or not callback or len(items) >= max_items:
            break

        time.sleep(1)

    return items[:max_items]


def _kr_parse_item(item, default_score):
    """把接口条目转成入库结构；识别不出标题/链接时返回 None"""
    material = item.get("templateMaterial") or {}
    item_id = item.get("itemId") or material.get("itemId")
    title = (material.get("widgetTitle") or "").strip()
    if not title or not item_id:
        return None

    # 快讯 itemType=20 → /newsflashes/；其余（文章为 10）→ /p/
    is_flash = item.get("itemType") == 20
    url = f"https://36kr.com/newsflashes/{item_id}" if is_flash else f"https://36kr.com/p/{item_id}"

    # publishTime 为毫秒时间戳
    publish_time = material.get("publishTime")
    if publish_time:
        try:
            time_str = datetime.datetime.fromtimestamp(publish_time / 1000).strftime("%Y-%m-%d %H:%M")
        except Exception:
            time_str = ""
    else:
        time_str = ""

    summary = (material.get("summary") or material.get("widgetContent") or "").strip()

    return {
        "title": title,
        "summary": summary[:500],
        "url": url,
        "source": "36 氪",
        "time": time_str,
        "score": default_score,
        "author": (material.get("authorName") or "").strip(),
        "like_count": 0,
        "comment_count": 0
    }


# 爬取 36kr 最新文章
def fetch_36kr():
    """爬取 36 氪文章（科技栏目 + 快讯）

    原方案抓 36kr.com 的 RSS/HTML，现全站被 JS 反爬挑战拦截（任何路径都返回同一个
    验证页，feedparser 静默拿到 0 条），因此改用官方网关接口。
    """
    articles = []
    try:
        # 科技栏目文章
        for nick in KR_SUBNAV_NICKS:
            param = {
                "siteId": 1,
                "platformId": 2,
                "subnavType": 1,
                "subnavNick": nick,
            }
            items = _kr_fetch_items(KR_SUBNAV_FLOW, param, KR_ARTICLE_QUOTA)
            for item in items:
                parsed = _kr_parse_item(item, default_score=60)
                if parsed:
                    articles.append(parsed)
            if nick != KR_SUBNAV_NICKS[-1]:
                time.sleep(1)

        # 快讯
        flash_items = _kr_fetch_items(
            KR_NEWSFLASH_FLOW,
            {"siteId": 1, "platformId": 2},
            KR_NEWSFLASH_QUOTA
        )
        for item in flash_items:
            parsed = _kr_parse_item(item, default_score=55)
            if parsed:
                articles.append(parsed)

    except Exception as e:
        print(f"爬取 36 氪失败：{e}")

    # 去重：同 url 去重，再按标题去重（同一条可能同时出现在栏目流和快讯流）
    seen_urls = set()
    seen_titles = set()
    unique_articles = []
    for article in articles:
        if article["url"] in seen_urls or article["title"] in seen_titles:
            continue
        seen_urls.add(article["url"])
        seen_titles.add(article["title"])
        unique_articles.append(article)

    articles = unique_articles[:MAX_ARTICLES_PER_SOURCE]

    print(f"✅ 爬取到 {len(articles)} 篇 36 氪文章")
    return articles


# 爬取澎湃新闻科技频道
def fetch_thepaper():
    """爬取澎湃新闻科技频道文章"""
    articles = []
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        
        # 澎湃新闻科技频道
        url = "https://www.thepaper.cn/list/119908"
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 从 __NEXT_DATA__ script 标签中提取 JSON 数据
            script_tag = soup.find("script", id="__NEXT_DATA__")
            if script_tag:
                data = json.loads(script_tag.string)
                article_list = data.get("props", {}).get("pageProps", {}).get("data", {}).get("list", [])
                
                for item in article_list[:MAX_ARTICLES_PER_SOURCE]:
                    cont_id = item.get("contId", "")
                    title = item.get("name", "")
                    pub_time_long = item.get("pubTimeLong", 0)
                    praise_times = item.get("praiseTimes", 0)
                    node_name = item.get("nodeInfo", {}).get("name", "")
                    
                    # 将毫秒时间戳转换为绝对时间格式
                    if pub_time_long:
                        pub_time = datetime.datetime.fromtimestamp(pub_time_long / 1000).strftime("%Y-%m-%d %H:%M")
                    else:
                        pub_time = ""
                    
                    if not cont_id or not title:
                        continue
                    
                    # 构建文章 URL
                    article_url = f"https://www.thepaper.cn/newsDetail_forward_{cont_id}"
                    
                    # 从详情页获取摘要
                    summary = ""
                    try:
                        detail_resp = requests.get(article_url, headers=headers, timeout=10, verify=False)
                        if detail_resp.status_code == 200:
                            detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
                            detail_script = detail_soup.find("script", id="__NEXT_DATA__")
                            if detail_script:
                                detail_data = json.loads(detail_script.string)
                                content_detail = detail_data.get("props", {}).get("pageProps", {}).get("detailData", {}).get("contentDetail", {})
                                summary = content_detail.get("summary", "")[:500]
                        time.sleep(0.3)  # 避免请求过快
                    except Exception as e:
                        print(f"获取澎湃文章摘要失败：{e}")
                    
                    # 计算分数：基础分 + 点赞数/10
                    score = 60 + int(praise_times) // 10
                    
                    articles.append({
                        "title": title,
                        "summary": summary,
                        "url": article_url,
                        "source": "澎湃",
                        "time": pub_time,
                        "score": score,
                        "author": "",
                        "like_count": int(praise_times),
                        "comment_count": 0
                    })
        
    except Exception as e:
        print(f"爬取澎湃新闻失败：{e}")
    
    print(f"✅ 爬取到 {len(articles)} 篇澎湃新闻文章")
    return articles


# 爬取人民网观点频道
def get_article_summary_from_detail(url, headers):
    """从详情页获取文章摘要（前 2-3 段，约 200 字）和发布时间"""
    summary = ""
    time_str = ""
    
    try:
        # 使用 HTTP（人民网 HTTPS 证书问题）
        if url.startswith('https://'):
            url = url.replace('https://', 'http://')
        
        response = requests.get(url, headers=headers, timeout=15)
        
        # 尝试多种编码
        try:
            html_content = response.content.decode('GB18030')
        except Exception:
            try:
                html_content = response.content.decode('GBK')
            except Exception:
                html_content = response.content.decode('UTF-8', errors='replace')
        
        soup = BeautifulSoup(html_content, "html.parser")
        
        # 提取发布时间 <b id="newstime">2026年03月28日08:58</b>
        time_elem = soup.select_one('#newstime')
        if time_elem:
            time_str = time_elem.get_text().strip()
            # 格式化时间：2026年03月28日08:58 -> 2026年03月28日 08:58
            time_str = re.sub(r'(日)(\d{2}:)', r'\1 \2', time_str)
        
        # 找正文内容 - 人民网主要在 #rm_txt_zw
        content_elem = soup.select_one('#rm_txt_zw')
        
        if not content_elem:
            # 备用选择器
            content_selectors = [
                '.article-content',
                '.text',
                '.content',
                'div[class*="article"]',
            ]
            for selector in content_selectors:
                elem = soup.select_one(selector)
                if elem and len(elem.get_text().strip()) > 200:
                    content_elem = elem
                    break
        
        if not content_elem:
            return summary, time_str
        
        # 获取前 2-3 段作为摘要
        paragraphs = []
        for p in content_elem.find_all('p'):
            text = p.get_text().strip()
            # 过滤掉无关内容
            if len(text) > 50 and not any(k in text for k in [
                '人民网', '版权所有', '举报', '点击这里', '分享到', 
                '责编', '客户端', '扫描', '二维码', '举报电话'
            ]):
                paragraphs.append(text)
                if len(paragraphs) >= 3:  # 只取前 3 段
                    break
        
        if paragraphs:
            # 合并并限制长度在 200 字左右
            summary = ' '.join(paragraphs[:2])
            if len(summary) > 200:
                summary = summary[:200] + '...'
        
        return summary, time_str
        
    except Exception as e:
        print(f"获取摘要失败：{url} - {e}")
        return summary, time_str


def fetch_people_opinion():
    """爬取人民网观点频道文章"""
    articles = []
    seen_urls = set()
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        
        # 人民网观点频道首页（主爬取源）
        base_urls = [
            "http://opinion.people.com.cn/GB/159301/index.html",  # 观点频道第1页
        ]
        # 添加更多页（共爬取5页）
        for i in range(2, 6):
            base_urls.append(f"http://opinion.people.com.cn/GB/159301/index{i}.html")

        for page_url in base_urls:
            try:
                response = requests.get(page_url, headers=headers, timeout=15)

                if response.status_code == 200:
                    # 使用 GBK 编码解码
                    try:
                        html_content = response.content.decode('GB18030')
                    except Exception:
                        try:
                            html_content = response.content.decode('GBK')
                        except Exception:
                            html_content = response.content.decode('UTF-8', errors='replace')

                    soup = BeautifulSoup(html_content, "html.parser")

                    # 获取所有链接
                    all_links = soup.find_all('a', href=True)

                    for link in all_links:
                        href = link.get('href', '')

                        # 只抓取包含 n1/ 的文章链接
                        if 'n1/' not in href and '/n/' not in href:
                            continue

                        title = link.text.strip()

                        # 过滤无效标题
                        if not title or len(title) < 6:
                            continue

                        url = urljoin(page_url, href)
                        if not url or url in seen_urls or 'people.com.cn' not in url:
                            continue
                        seen_urls.add(url)

                        # 获取摘要和时间（访问详情页）
                        summary, detail_time = get_article_summary_from_detail(url, headers)

                        time_str = detail_time if detail_time else ""

                        articles.append({
                            "title": title,
                            "summary": summary,
                            "url": url,
                            "source": "人民网",
                            "time": time_str,
                            "score": 80,
                            "author": "",
                            "like_count": 0,
                            "comment_count": 0
                        })

                        if len(articles) >= MAX_ARTICLES_PER_SOURCE * 3:  # 允许更多历史文章
                            break

                time.sleep(0.5)  # 页面间延迟，避免请求过快

            except Exception as e:
                print(f"爬取页面 {page_url} 失败：{e}")
                continue

        print(f"📰 从人民网观点频道爬取到 {len(articles)} 篇文章")
                        
    except Exception as e:
        print(f"爬取人民网失败：{e}")
    
    print(f"✅ 爬取到 {len(articles)} 篇人民网文章")
    return articles


def main():
    print("=" * 60)
    print(f"🕒 开始时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 爬取科技资讯（少数派 + 36 氪）
    print("\n📱 正在爬取科技资讯...")
    print("-" * 60)
    
    sspai_articles = fetch_sspai()
    time.sleep(1)
    
    kr_articles = fetch_36kr()
    time.sleep(1)
    
    thepaper_articles = fetch_thepaper()
    
    tech_articles = sspai_articles + kr_articles + thepaper_articles
    print(f"📊 科技资讯共计：{len(tech_articles)} 篇")
    
    # 保存到数据库
    if tech_articles:
        saved_count = save_to_database(tech_articles, 'tech')
        print(f"💾 成功入库：{saved_count} 篇科技资讯")
    
    # 爬取时政观点（人民网）
    print("\n🇨🇳 正在爬取时政观点...")
    print("-" * 60)
    
    people_articles = fetch_people_opinion()
    print(f"📊 时政观点共计：{len(people_articles)} 篇")
    
    # 保存到数据库
    if people_articles:
        saved_count = save_to_database(people_articles, 'people')
        print(f"💾 成功入库：{saved_count} 篇时政观点")
    
    # 统计信息
    print("\n" + "=" * 60)
    print("📈 本次爬取统计:")
    print(f"   科技资讯：爬取 {len(tech_articles)} 篇")
    print(f"   时政观点：爬取 {len(people_articles)} 篇")
    print(f"   总计：{len(tech_articles) + len(people_articles)} 篇")
    print("=" * 60)
    
    # 处理原创文章
    print("\n📝 正在检查原创文章...")
    print("-" * 60)
    original_new_count = 0
    try:
        import subprocess
        result = subprocess.run(
            ['python3', '/home/ubuntu/process_original_articles.py'],
            cwd='/home/ubuntu',
            capture_output=True,
            text=True,
            timeout=300
        )
        print(result.stdout)
        if result.stderr:
            print(f"⚠️  {result.stderr}")
        # 从输出中提取新增数量
        for line in result.stdout.split('\n'):
            if '新增' in line and '篇文章' in line:
                try:
                    original_new_count = int(line.split('新增')[1].split('篇')[0].strip())
                except Exception:
                    pass
    except Exception as e:
        print(f"⚠️  处理原创文章异常：{e}")
    
    print(f"✅ 完成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 自动触发页面重建（如果有新文章）
    total_new = len(tech_articles) + len(people_articles) + original_new_count
    if total_new > 0:
        print("\n🔄 正在自动重建页面...")
        try:
            import subprocess
            result = subprocess.run(
                ['python3', '/home/ubuntu/rebuild_pages.py'],
                cwd='/home/ubuntu',
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                print("✅ 页面重建成功")
            else:
                print(f"⚠️  页面重建失败：{result.stderr}")
        except Exception as e:
            print(f"⚠️  自动重建页面异常：{e}")


if __name__ == "__main__":
    main()
