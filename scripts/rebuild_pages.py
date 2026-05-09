#!/usr/bin/env python3
import pymysql
import re
from jinja2 import Environment, FileSystemLoader

CONFIG = {
    'output_dir': '/var/www/binjian.cloud',
    'templates_dir': '/var/www/binjian.cloud/templates',
    'mysql': {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'root',
        'password': '19930107ZBj',
        'database': 'articles',
        'charset': 'utf8mb4',
    }
}

# 摘要最大字符数（约3行）
SUMMARY_MAX_LENGTH = 150

def truncate_summary(summary, max_length=SUMMARY_MAX_LENGTH):
    """截取摘要到指定长度，并清理可能导致移动端溢出的内容"""
    if not summary:
        return ''
    # 去除 Markdown 图片语法
    summary = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', summary)
    # 去除 URL
    summary = re.sub(r'https?://\S+', '', summary)
    # 去除 @username
    summary = re.sub(r'@\w+', '', summary)
    # 在日期后插入空格（如 "2026-04-17By" -> "2026-04-17 By"）
    summary = re.sub(r'(\d{4}-\d{2}-\d{2})([A-Za-z])', r'\1 \2', summary)
    # 在连续中文和英文之间不太容易断行的地方加空格（数字+大写字母）
    summary = re.sub(r'(\d)([A-Z][a-z])', r'\1 \2', summary)
    # 清理多余空白
    summary = re.sub(r'\s+', ' ', summary).strip()
    if len(summary) <= max_length:
        return summary
    return summary[:max_length] + '...'

def format_date(date_str):
    """统一日期格式为：2026年03月30日 14:30"""
    if not date_str:
        return ''
    date_str = str(date_str)
    
    # 已经是目标格式（包含年月日）
    if '年' in date_str and '月' in date_str and '日' in date_str:
        import re
        # 尝试提取时分：2026年03月30日 14:30 或 2026年03月30日14:30
        match = re.match(r'(\d{4})年(\d{2})月(\d{2})日\s*(\d{2}:\d{2})?', date_str)
        if match:
            year, month, day, time_part = match.groups()
            if time_part:
                return f"{year}年{month}月{day}日 {time_part}"
            return f"{year}年{month}月{day}日"
        return date_str[:11] if len(date_str) > 11 else date_str
    
    # 格式：2026-03-30 17:06 或 2026-03-30
    if '-' in date_str:
        parts = date_str.split('-')
        if len(parts) >= 3:
            year = parts[0]
            month = parts[1]
            day_and_time = parts[2].split()
            day = day_and_time[0]
            # 检查是否有时分
            time_part = day_and_time[1] if len(day_and_time) > 1 else ''
            if time_part and len(time_part) >= 5:
                return f"{year}年{month}月{day}日 {time_part[:5]}"
            return f"{year}年{month}月{day}日"
    
    return date_str[:10] if len(date_str) > 10 else date_str

PAGE_CONFIGS = {
    'tech': {
        'output_file': 'tech-news.html',
        'title': '📱 科技资讯',
        'description': '科技资讯精选 - 来自少数派、36氪的最新科技文章',
        'theme_color': '#667eea',
        'theme_color_secondary': '#764ba2',
        'update_schedule': '每日更新',
        'page_type': 'tech',
        'canonical_path': '/tech-news.html',
    },
    'people': {
        'output_file': 'people-news.html',
        'title': '🇨🇳 时政观点',
        'description': '人民网观点频道 - 权威声音，每日更新',
        'theme_color': '#c8102e',
        'theme_color_secondary': '#8b0000',
        'update_schedule': '每日更新',
        'page_type': 'people',
        'canonical_path': '/people-news.html',
    },
    'original': {
        'output_file': 'articles.html',
        'title': '📝 原创文章',
        'description': 'Binjian 原创文章 - 分享效率工具、知识管理、AI应用与生活感悟',
        'theme_color': '#16a34a',
        'theme_color_secondary': '#047857',
        'update_schedule': '不定期更新',
        'page_type': 'articles',
        'canonical_path': '/articles.html',
    }
}

# 连接数据库
conn = pymysql.connect(**CONFIG['mysql'], cursorclass=pymysql.cursors.DictCursor)
generator = Environment(loader=FileSystemLoader(CONFIG['templates_dir']), autoescape=True)

# 科技资讯页面
with conn.cursor() as cursor:
    cursor.execute('SELECT * FROM news_articles WHERE page_type = "tech" ORDER BY publish_time DESC, score DESC LIMIT 1000')
    unique_tech = cursor.fetchall()
    for item in unique_tech:
        item['time'] = format_date(item['publish_time'])
        item['summary'] = truncate_summary(item.get('summary', ''))

template = generator.get_template('news_page.html')
html = template.render(
    articles=unique_tech,
    page_title=PAGE_CONFIGS['tech']['title'],
    page_description=PAGE_CONFIGS['tech']['description'],
    page_type=PAGE_CONFIGS['tech']['page_type'],
    theme_color=PAGE_CONFIGS['tech']['theme_color'],
    theme_color_secondary=PAGE_CONFIGS['tech']['theme_color_secondary'],
    update_time=__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    update_schedule=PAGE_CONFIGS['tech']['update_schedule'],
    canonical_path=PAGE_CONFIGS['tech']['canonical_path'],
    CONFIG={
        'articles_per_page': 20
    }
)

with open(f"{CONFIG['output_dir']}/{PAGE_CONFIGS['tech']['output_file']}", 'w', encoding='utf-8') as f:
    f.write(html)
print("✅ 已重新生成: " + PAGE_CONFIGS['tech']['output_file'])

# 时政观点页面
with conn.cursor() as cursor:
    cursor.execute('SELECT * FROM news_articles WHERE page_type = "people" ORDER BY publish_time DESC, score DESC LIMIT 1000')
    people_articles = cursor.fetchall()
    for item in people_articles:
        item['time'] = format_date(item['publish_time'])
        item['summary'] = truncate_summary(item.get('summary', ''))

template = generator.get_template('news_page.html')
html = template.render(
    articles=people_articles,
    page_title=PAGE_CONFIGS['people']['title'],
    page_description=PAGE_CONFIGS['people']['description'],
    page_type=PAGE_CONFIGS['people']['page_type'],
    theme_color=PAGE_CONFIGS['people']['theme_color'],
    theme_color_secondary=PAGE_CONFIGS['people']['theme_color_secondary'],
    update_time=__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    update_schedule=PAGE_CONFIGS['people']['update_schedule'],
    canonical_path=PAGE_CONFIGS['people']['canonical_path'],
    CONFIG={
        'articles_per_page': 20
    }
)

with open(f"{CONFIG['output_dir']}/{PAGE_CONFIGS['people']['output_file']}", 'w', encoding='utf-8') as f:
    f.write(html)
print("✅ 已重新生成: " + PAGE_CONFIGS['people']['output_file'])

# 原创文章页面
with conn.cursor() as cursor:
    cursor.execute('SELECT * FROM news_articles WHERE page_type = "original" ORDER BY publish_time DESC, score DESC LIMIT 1000')
    original_articles = cursor.fetchall()
    for item in original_articles:
        item['time'] = format_date(item['publish_time'])
        item['summary'] = truncate_summary(item.get('summary', ''))

template = generator.get_template('news_page.html')
html = template.render(
    articles=original_articles,
    page_title=PAGE_CONFIGS['original']['title'],
    page_description=PAGE_CONFIGS['original']['description'],
    page_type=PAGE_CONFIGS['original']['page_type'],
    theme_color=PAGE_CONFIGS['original']['theme_color'],
    theme_color_secondary=PAGE_CONFIGS['original']['theme_color_secondary'],
    update_time=__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    update_schedule=PAGE_CONFIGS['original']['update_schedule'],
    canonical_path=PAGE_CONFIGS['original']['canonical_path'],
    CONFIG={
        'articles_per_page': 20
    }
)

with open(f"{CONFIG['output_dir']}/{PAGE_CONFIGS['original']['output_file']}", 'w', encoding='utf-8') as f:
    f.write(html)
print("✅ 已重新生成: " + PAGE_CONFIGS['original']['output_file'])

conn.close()
print("\n所有页面重新生成完成，左侧导航都已添加时评精读入口")
