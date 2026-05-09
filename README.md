# binjian.cloud - 个人主页

这是我的个人主页，一个轻量级静态网站，集成了自动爬取资讯和原创文章管理功能。

🔗 在线访问：[https://binjian.cloud](https://binjian.cloud)

## 📋 项目概述

这是一个纯静态的个人网站，采用 Python 爬虫 + MySQL 存储 + Jinja2 模板渲染生成静态HTML的架构。内容分为三大板块：

- **🏠 首页** - 个人介绍和导航
- **📱 科技资讯** - 自动爬取少数派、36氪的最新科技文章
- **🇨🇳 时政观点** - 自动爬取人民网观点频道的权威评论
- **📝 原创文章** - 我的原创文章，通过 Markdown 编写自动转换为 HTML
- **📖 时评精读** - 每日精选精读文章存档

## 🛠️ 技术架构

```
┌─────────────────────────────────────────────────────┐
│                   定时爬虫任务                        │
│  - fetch_news.py: 每3小时爬取新闻                    │
│  - process_original_articles.py: 处理原创 Markdown   │
│  - rebuild_pages.py: 重新生成所有静态页面            │
└────────────────────────────┬────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────┐
│                    MySQL 数据库                       │
│  - news_articles 表存储所有文章信息                   │
│  - 去重策略：基于 URL 判断是否已存在                   │
└────────────────────────────┬────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────┐
│               Jinja2 模板渲染                         │
│  - templates/news_page.html: 文章列表页模板          │
│  - 从数据库读取最新数据，渲染生成静态 HTML             │
└────────────────────────────┬────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────┐
│                 Nginx 静态网站服务                    │
│  - 直接托管生成的静态 HTML/CSS/JS                     │
│  - 支持 HTTPS，响应速度极快                           │
└─────────────────────────────────────────────────────┘
```

## 📁 目录结构

```
/var/www/binjian.cloud/          # 网站根目录 (Nginx 指向这里)
├── index.html                  # 首页
├── tech-news.html              # 科技资讯页面 (自动生成)
├── people-news.html            # 时政观点页面 (自动生成)
├── articles.html               # 原创文章列表页 (自动生成)
├── daily.html                  # 时评精读页面
├── article/                    # 原创文章详情页 (自动生成)
├── css/                        # 样式文件
├── js/                         # JavaScript 文件
├── templates/                  # Jinja2 模板
│   ├── base.html              # 基础模板
│   └── news_page.html         # 新闻列表页模板
├── icons.png                  # 网站图标
├── profile.png                # 个人头像
└── README.md                  # 本文件

/home/ubuntu/                    # 爬虫脚本目录
├── fetch_news.py              # 主爬虫脚本，爬取新闻
├── process_original_articles.py  # 处理原创 Markdown 文章
├── rebuild_pages.py           # 重新生成所有静态页面
├── daily_articles/            # 每日精读文章存档
├── original_articles/         # 原创 Markdown 文章存放目录
├── daily_people_article_push_v3.py  # 每日推送脚本
├── batch_generate_daily.py    # 批量生成日刊
├── fetch_news.log             # 爬虫运行日志
└── backup_database.sh         # 数据库备份脚本
```

## 🔄 自动更新流程

### 1. 定时爬取新闻

**定时任务**：通过 `crontab` 每3小时执行一次：

```bash
0 */3 * * * cd /home/ubuntu && python3 fetch_news.py >> /home/ubuntu/fetch_news.log 2>&1
```

**爬取来源**：

| 来源 | 类型 | 说明 |
|------|------|------|
| 少数派 | 科技资讯 | 通过官方 API 获取，自带点赞和评论数 |
| 36氪 | 科技资讯 | 通过 RSS 获取 |
| 人民网观点频道 | 时政观点 | 爬取文章列表后进入详情页提取摘要 |

**工作流程**：

1. 爬取各个来源的最新文章
2. 去重检查：通过 URL 判断文章是否已在数据库中
3. 将新文章插入 MySQL 数据库
4. 自动调用 `process_original_articles.py` 处理新增原创文章
5. 如果有新增文章，自动调用 `rebuild_pages.py` 重新生成静态页面

### 2. 原创文章处理

当你在 `/home/ubuntu/original_articles/` 目录添加了新的 `.md` 文件：

1. `fetch_news.py` → `process_original_articles.py` 被自动调用
2. 扫描目录下所有 `.md` 文件
3. 提取标题（从一级标题）和摘要（前两段正文）
4. 使用 `markdown` 库将 Markdown 转换为 HTML
5. 使用预定义模板生成完整的文章详情页，保存到 `/var/www/binjian.cloud/article/`
6. 将文章信息插入数据库（`page_type = original`）
7. 后续触发页面重建

### 3. 页面重建

`rebuild_pages.py` 做这些事情：

1. 从 MySQL 按类型（tech/people/original）分别读取最新文章（按发布时间倒序，最多保留 1000 篇）
2. 使用 Jinja2 模板渲染三个列表页：
   - `tech-news.html` - 科技资讯
   - `people-news.html` - 时政观点  
   - `articles.html` - 原创文章
3. 写入文件到网站目录，Nginx 直接提供访问

### 4. 数据去重策略

- 爬取新闻：基于 URL 去重，同一 URL 不会重复入库
- 原创文章：基于生成的 URL 哈希去重，同一文件不会重复处理
- 每次重建页面都是全量重建，保证数据一致性

## 🗄️ 数据库设计

`articles` 数据库，`news_articles` 表结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键自增 |
| title | varchar(500) | 文章标题 |
| summary | text | 文章摘要 |
| url | varchar(500) | 文章链接（去重键） |
| source | varchar(100) | 来源 |
| publish_time | varchar(100) | 发布时间 |
| author | varchar(100) | 作者 |
| like_count | int | 点赞数 |
| comment_count | int | 评论数 |
| score | int | 排序分数（用于加权排序） |
| page_type | varchar(20) | 页面类型：tech/people/original |

## 🎨 前端特性

- 🌓 **支持暗色/亮色主题切换** - 记住用户偏好
- 📱 **全响应式设计** - 完美适配桌面端和移动端
- ⚡ **纯静态HTML** - 加载速度极快，无需后端
- 🔍 **SEO友好** - 完整的 meta 标签和结构化数据
- 🎯 **分页加载** - 每页20篇，滚动自动加载更多

## 📝 如何添加原创文章

1. 在 `/home/ubuntu/original_articles/` 目录新建 `.md` 文件
2. 编写 Markdown 内容，一级标题作为文章标题
   ```markdown
   # 文章标题

   这里是文章正文，会自动提取前两段作为摘要...

   ## 二级标题

   更多内容...
   ```
3. 等待下一次定时任务执行，或者手动执行：
   ```bash
   cd /home/ubuntu && python3 process_original_articles.py
   python3 rebuild_pages.py
   ```
4. 网页自动更新完成 ✅

## 🔧 本地开发/部署

### 依赖安装

```bash
# Python 依赖
pip install requests beautifulsoup4 pymysql jinja2 markdown feedparser
```

### 配置数据库

修改脚本中的数据库连接配置：

```python
# fetch_news.py, process_original_articles.py, rebuild_pages.py 都有
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '你的密码',
    'database': 'articles',
    'charset': 'utf8mb4'
}
```

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name binjian.cloud www.binjian.cloud;
    root /var/www/binjian.cloud;
    index index.html;
    
    # 静态资源缓存
    location ~* \.(css|js|png|jpg|jpeg|gif|ico)$ {
        expires 7d;
        add_header Cache-Control public;
    }
}

# HTTPS 由 Certbot 自动配置
```

## 📊 数据备份

`backup_database.sh` 脚本会自动备份数据库到 `/home/ubuntu/database_backups/`，建议配置定时任务每周备份一次。

## 📈 特色功能

### 随机跳转
原创文章详情页支持**随机跳转**功能，点击按钮随机滚动到文章任意位置，适合发现式阅读。

### 主题持久化
用户选择的主题会存在 localStorage，刷新页面保持不变。

### 无限滚动
文章列表页采用滚动加载，每次加载20篇，体验流畅。

## 📧 联系方式

- 网站：[https://binjian.cloud](https://binjian.cloud)
- 作者：张彬健 (Binjian)

## 📄 许可证

本项目仅供个人学习使用。
