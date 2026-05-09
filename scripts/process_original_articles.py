#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
原创文章处理脚本 - 扫描 original_articles 目录，将 Markdown 转换为 HTML 并入库
流程：扫描 MD 文件 → 生成 HTML 详情页 → 入库 → 等待 rebuild_pages.py 重建列表页
"""

import os
import hashlib
import datetime
import re
import pymysql
import markdown

# 配置
CONFIG = {
    'original_dir': '/home/ubuntu/original_articles',
    'output_dir': '/var/www/binjian.cloud',
    'article_dir': '/var/www/binjian.cloud/article',
    'mysql': {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'root',
        'password': '19930107ZBj',
        'database': 'articles',
        'charset': 'utf8mb4',
    }
}

# HTML 模板
ARTICLE_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{description}">
    <meta name="author" content="张彬健">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:type" content="article">
    <meta property="og:locale" content="zh_CN">
    <meta property="og:site_name" content="张彬健的个人主页">
    <meta property="article:author" content="张彬健">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">
    <link rel="canonical" href="https://binjian.cloud{url}">
    <title>{title} - 张彬健</title>
    <link rel="icon" href="/icons.png" type="image/png">
    <link rel="stylesheet" href="/css/common.css">
    <!-- JSON-LD 结构化数据 -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "{title}",
        "author": {{
            "@type": "Person",
            "name": "张彬健",
            "alternateName": "Binjian"
        }},
        "datePublished": "{date}",
        "description": "{description}"
    }}
    </script>
    
<style>
    /* 文章详情页主题色 */
    :root {{
        --accent-color: #16a34a;
        --accent-gradient: linear-gradient(135deg, #16a34a 0%, #047857 100%);
    }}
    
    /* 文章详情容器 */
    .article-container {{
        max-width: 900px;
        margin: 24px auto;
        padding: 0 20px;
    }}
    
    /* 文章头部 */
    .article-header {{
        background: var(--card-bg);
        border-radius: 8px;
        border: 1px solid var(--border-color);
        padding: 32px;
        margin-bottom: 24px;
    }}
    
    .article-title {{
        font-size: 32px;
        font-weight: 700;
        color: var(--text-color);
        line-height: 1.4;
        margin-bottom: 16px;
    }}
    
    .article-meta {{
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        color: var(--muted-text);
        font-size: 14px;
        margin-bottom: 0;
    }}
    
    /* 文章内容 */
    .article-content {{
        background: var(--card-bg);
        border-radius: 8px;
        border: 1px solid var(--border-color);
        padding: 32px;
        line-height: 1.8;
        font-size: 17px;
        color: var(--text-color);
    }}
    
    .article-content h1 {{
        font-size: 28px;
        margin: 32px 0 16px;
        padding-bottom: 8px;
        border-bottom: 1px solid var(--border-color);
    }}
    
    .article-content h2 {{
        font-size: 24px;
        margin: 28px 0 14px;
        color: var(--text-color);
    }}
    
    .article-content h3 {{
        font-size: 20px;
        margin: 24px 0 12px;
        color: var(--text-color);
    }}
    
    .article-content h4 {{
        font-size: 18px;
        margin: 20px 0 10px;
        color: var(--text-color);
    }}
    
    .article-content p {{
        margin-bottom: 16px;
    }}
    
    .article-content ul, .article-content ol {{
        margin-bottom: 16px;
        padding-left: 24px;
    }}
    
    .article-content li {{
        margin-bottom: 8px;
    }}
    
    .article-content pre {{
        background: var(--bg-color);
        padding: 16px;
        border-radius: 6px;
        overflow-x: auto;
        margin-bottom: 16px;
    }}
    
    .article-content code {{
        background: var(--bg-color);
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.9em;
    }}
    
    .article-content pre code {{
        background: transparent;
        padding: 0;
    }}
    
    .article-content blockquote {{
        border-left: 4px solid var(--accent-color);
        padding-left: 16px;
        color: var(--secondary-text);
        margin: 16px 0;
        background: var(--bg-color);
        padding: 12px 16px;
        border-radius: 0 6px 6px 0;
    }}
    
    .article-content img {{
        max-width: 100%;
        border-radius: 6px;
        margin: 16px 0;
    }}
    
    .article-content table {{
        border-collapse: collapse;
        width: 100%;
        margin: 16px 0;
    }}
    
    .article-content table th,
    .article-content table td {{
        border: 1px solid var(--border-color);
        padding: 8px 12px;
    }}
    
    .article-content table th {{
        background: var(--bg-color);
    }}
    
    .article-content hr {{
        border: none;
        border-top: 1px solid var(--border-color);
        margin: 32px 0;
    }}
    
    /* 特殊样式：佳句、解析块 */
    .article-content h3 + p,
    .article-content h4 + p {{
        margin-top: 8px;
    }}
    
    /* 返回链接 */
    .back-link {{
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    
    .back-link a {{
        color: var(--accent-color);
        text-decoration: none;
        font-size: 15px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }}
    
    .back-link a:hover {{
        text-decoration: underline;
    }}
    
    /* 随机跳转按钮 */
    .random-jump-btn {{
        background: var(--accent-gradient);
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 6px;
        font-size: 14px;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        transition: all 0.2s;
    }}
    
    .random-jump-btn:hover {{
        box-shadow: 0 4px 12px rgba(22, 163, 74, 0.3);
        transform: translateY(-1px);
    }}
    
    .random-jump-btn:active {{
        transform: translateY(0);
    }}
    
    /* 回到顶部按钮 */
    .back-to-top {{
        position: fixed;
        bottom: 24px;
        right: 24px;
        width: 48px;
        height: 48px;
        background: var(--accent-gradient);
        color: white;
        border: none;
        border-radius: 50%;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(22, 163, 74, 0.3);
        transition: all 0.3s;
        opacity: 0.9;
        z-index: 999;
    }}
    
    .back-to-top:hover {{
        opacity: 1;
        box-shadow: 0 6px 16px rgba(22, 163, 74, 0.4);
        transform: translateY(-2px);
    }}
    
    /* 响应式 */
    @media (max-width: 768px) {{
        .article-header {{
            padding: 20px;
        }}
        
        .article-title {{
            font-size: 24px;
        }}
        
        .article-content {{
            padding: 20px;
            font-size: 16px;
        }}
    }}
</style>

</head>
<body>
    <!-- 移动端顶部栏 -->
    <div class="top-bar" id="topBar">
        <button class="menu-toggle" id="menuToggle" title="显示菜单" aria-label="打开导航菜单" aria-expanded="false">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
        </button>
        <span class="page-title" id="pageTitle">{title}</span>
        <button class="theme-toggle-mobile" id="themeToggleMobile" title="切换主题" aria-label="切换主题" aria-pressed="false">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
        </button>
    </div>

    <div class="container">
        <!-- 统一导航栏 -->
        <div class="nav-sidebar" id="navSidebar">
            <nav class="nav-bar" aria-label="主导航">
                <a href="/" class="nav-btn">🏠 返回主页</a>
                <a href="/people-news.html" class="nav-btn">🇨🇳 时政观点</a>
                <a href="/tech-news.html" class="nav-btn">📱 科技资讯</a>
                <a href="/daily.html" class="nav-btn">📖 时评精读</a>
                <a href="/articles.html" class="nav-btn active">📝 原创文章</a>
                <button class="theme-toggle" id="themeToggle" title="切换主题" aria-label="切换主题" aria-pressed="false">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
                    <span class="theme-text">主题</span>
                </button>
            </nav>
        </div>

        
<main class="article-container">
    <div class="back-link">
        <a href="/articles.html">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
            返回原创文章列表
        </a>
        <button class="random-jump-btn" id="randomJumpBtn" title="随机跳转到文章任意位置">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
            随机跳转
        </button>
    </div>
    
    <header class="article-header">
        <h1 class="article-title">{title}</h1>
        <div class="article-meta">
            <span>🕒 {date}</span>
        </div>
    </header>
    
    <article class="article-content">
{content}
    </article>
</main>

    </div>
    
    <!-- 回到顶部按钮 -->
    <button class="back-to-top" id="backToTop" title="回到顶部" aria-label="回到顶部">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>
    </button>

    <script src="/js/common.js"></script>
    <script>
        // 回到顶部按钮
        const backToTop = document.getElementById('backToTop');
        window.addEventListener('scroll', () => {{
            if (window.scrollY > 300) {{
                backToTop.style.display = 'flex';
            }} else {{
                backToTop.style.display = 'none';
            }}
        }});
        backToTop.addEventListener('click', () => {{
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }});
        // 初始状态
        backToTop.style.display = 'none';
        
        // 随机跳转按钮
        const randomJumpBtn = document.getElementById('randomJumpBtn');
        const articleContent = document.querySelector('.article-content');
        
        randomJumpBtn.addEventListener('click', () => {{
            if (!articleContent) return;
            
            // 获取文章内容的高度
            const contentHeight = articleContent.scrollHeight;
            const viewportHeight = window.innerHeight;
            const maxScroll = contentHeight - viewportHeight + 200; // 加上偏移量
            
            if (maxScroll <= 0) return;
            
            // 生成随机位置
            const randomPosition = Math.floor(Math.random() * maxScroll);
            
            // 计算文章内容区距离顶部的偏移
            const contentOffset = articleContent.getBoundingClientRect().top + window.scrollY;
            
            // 滚动到随机位置
            window.scrollTo({{ 
                top: contentOffset + randomPosition,
                behavior: 'smooth'
            }});
        }});
    </script>
</body>
</html>'''


def get_db_connection():
    """获取数据库连接"""
    try:
        conn = pymysql.connect(**CONFIG['mysql'])
        return conn
    except Exception as e:
        print(f"数据库连接失败：{e}")
        return None


def extract_title_from_md(md_content, filename):
    """从 Markdown 内容提取标题"""
    lines = md_content.strip().split('\n')
    
    # 先尝试找一级标题，但要排除看起来像章节标题的（如 "一、"、"二、" 开头）
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('# '):
            title = line[2:].strip()
            # 如果标题以数字章节开头（如 "一、改革方法"），使用文件名
            if re.match(r'^[一二三四五六七八九十]+[、．.]', title):
                break
            return title
    
    # 移除 .md 后缀作为标题
    return filename.replace('.md', '')


def extract_summary(md_content, max_length=300):
    """从 Markdown 内容提取摘要（取前几段有效文字）"""
    lines = md_content.strip().split('\n')
    paragraphs = []
    
    for line in lines:
        line = line.strip()
        # 跳过标题、空行、分隔线
        if not line or line.startswith('#') or line == '---':
            continue
        # 跳过列表项开头的摘要（通常是佳句、解析等）
        if line.startswith('###'):
            break
        # 收集正文段落
        if len(line) > 20:
            paragraphs.append(line)
            if len(paragraphs) >= 2:
                break
    
    summary = ' '.join(paragraphs)
    if len(summary) > max_length:
        summary = summary[:max_length] + '...'
    return summary


def md_to_html(md_content):
    """将 Markdown 转换为 HTML"""
    # 使用 markdown 库转换，支持表格、代码块等扩展
    html = markdown.markdown(
        md_content, 
        extensions=['extra', 'toc', 'nl2br']
    )
    return html


def generate_url_hash(title, date):
    """生成文章 URL hash"""
    hash_str = title + date
    return hashlib.md5(hash_str.encode('utf-8')).hexdigest()[:8]


def is_article_in_db(conn, url):
    """检查文章是否已在数据库中"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM news_articles WHERE url = %s", (url,))
            return cursor.fetchone() is not None
    except Exception as e:
        print(f"查询数据库失败：{e}")
        return False


def save_to_db(conn, title, summary, url, date):
    """保存文章到数据库"""
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO news_articles 
            (title, summary, url, source, publish_time, author, like_count, comment_count, score, page_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                title,
                summary,
                url,
                '原创',
                date,
                'Binjian',
                0,
                0,
                100,  # 原创文章默认高分
                'original'
            ))
            conn.commit()
            return True
    except Exception as e:
        print(f"入库失败：{e}")
        conn.rollback()
        return False


def process_markdown_file(filepath, conn):
    """处理单个 Markdown 文件"""
    filename = os.path.basename(filepath)
    
    # 读取文件
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            md_content = f.read()
    except Exception as e:
        print(f"❌ 读取文件失败 {filename}：{e}")
        return False
    
    # 提取信息
    title = extract_title_from_md(md_content, filename)
    summary = extract_summary(md_content)
    
    # 使用文件修改时间作为发布日期
    file_mtime = os.path.getmtime(filepath)
    date = datetime.datetime.fromtimestamp(file_mtime).strftime('%Y-%m-%d')
    
    # 生成 URL
    url_hash = generate_url_hash(title, date)
    url = f"/article/{url_hash}.html"
    html_filename = f"{url_hash}.html"
    html_path = os.path.join(CONFIG['article_dir'], html_filename)
    
    # 检查是否已处理
    if is_article_in_db(conn, url):
        print(f"⏭️  已存在：{title}")
        return False
    
    # 转换 Markdown 到 HTML
    content_html = md_to_html(md_content)
    
    # 生成完整 HTML
    full_html = ARTICLE_TEMPLATE.format(
        title=title,
        description=summary.replace('"', '&quot;'),
        date=date,
        url=url,
        content=content_html
    )
    
    # 确保 article 目录存在
    os.makedirs(CONFIG['article_dir'], exist_ok=True)
    
    # 写入 HTML 文件
    try:
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(full_html)
        print(f"✅ 生成 HTML：{html_filename}")
    except Exception as e:
        print(f"❌ 写入 HTML 失败：{e}")
        return False
    
    # 入库
    if save_to_db(conn, title, summary, url, date):
        print(f"✅ 入库成功：{title}")
        return True
    else:
        return False


def main():
    print("=" * 60)
    print(f"📝 原创文章处理脚本 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 检查目录
    if not os.path.exists(CONFIG['original_dir']):
        print(f"❌ 原创文章目录不存在：{CONFIG['original_dir']}")
        return
    
    # 获取数据库连接
    conn = get_db_connection()
    if not conn:
        print("❌ 无法连接数据库")
        return
    
    # 扫描 Markdown 文件
    md_files = [f for f in os.listdir(CONFIG['original_dir']) if f.endswith('.md')]
    
    if not md_files:
        print("📂 没有找到 Markdown 文件")
        conn.close()
        return
    
    print(f"📂 找到 {len(md_files)} 个 Markdown 文件")
    print("-" * 60)
    
    # 处理每个文件
    new_count = 0
    for md_file in sorted(md_files):
        filepath = os.path.join(CONFIG['original_dir'], md_file)
        if process_markdown_file(filepath, conn):
            new_count += 1
    
    # 关闭数据库连接
    conn.close()
    
    # 总结
    print("-" * 60)
    print(f"📊 处理完成：新增 {new_count} 篇文章")
    print("=" * 60)
    
    return new_count


if __name__ == "__main__":
    main()
