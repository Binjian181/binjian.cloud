# binjian.cloud - 个人主页

这是我的个人主页，一个轻量级静态网站，集成了自动爬取资讯和原创文章管理功能。

🔗 在线访问：[https://binjian.cloud](https://binjian.cloud)

## 📋 项目概述

这是一个纯静态的个人网站，采用 Python 爬虫 + 文件数据存储 + Jinja2 模板渲染生成静态 HTML 的架构，
定时任务和发布全部由 GitHub Actions 完成，站点由 GitHub Pages 托管。内容分为三大板块：

- **🏠 首页** - 个人介绍和导航
- **📱 科技资讯** - 自动爬取少数派、36氪的最新科技文章
- **🇨🇳 时政观点** - 自动爬取人民网观点频道的权威评论
- **📝 原创文章** - 我的原创文章，通过 Markdown 编写自动转换为 HTML
- **📖 时评精读** - 每日精选精读文章存档

## 🛠️ 技术架构

```
┌─────────────────────────────────────────────────────┐
│  GitHub Actions 定时任务（main 分支只有源码）         │
│  - fetch.yml：每 3 小时抓取新闻                      │
│  - daily-push.yml：北京时间 07:00 / 09:30 生成时评精读│
└────────────────────────────┬────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────┐
│  site-data 分支（单提交，每次覆盖，仓库体积不增长）   │
│  - articles.jsonl：文章记录，按类型限量保留           │
│  - seen_urls.txt：历史 URL，抓取去重                 │
│  - daily_list.json + daily/ + article/：已生成页面    │
└────────────────────────────┬────────────────────────┘
                             │ Jinja2 渲染
                             ▼
┌─────────────────────────────────────────────────────┐
│  gh-pages 分支 = GitHub Pages 站点根目录              │
│  - tech-news.html / people-news.html / articles.html  │
│  - daily.html / daily/ / article/ / css / js          │
│  - 不含脚本、模板与数据文件                            │
└─────────────────────────────────────────────────────┘
```

## 📁 目录结构

```
binjian.cloud/                  # main 分支：只有源码，运行产物不进版本库
├── index.html                  # 首页（手工维护）
├── profile.png / icons.png     # 头像与图标
├── css/ js/                    # 静态资源
├── templates/                  # Jinja2 模板
├── original_articles/          # 原创 Markdown 文章源文件
├── requirements.txt            # Actions 依赖清单
├── .github/workflows/
│   ├── fetch.yml               # 每 3 小时抓取并发布
│   └── daily-push.yml          # 每日时评精读
└── scripts/
    ├── store.py                # 文件型数据存储（替代 MySQL）
    ├── fetch_news.py           # 爬虫主流程
    ├── rebuild_pages.py        # 重新生成列表页
    ├── process_original_articles.py
    ├── daily_people_article_push_v3.py
    ├── build_site.py           # 组装发布目录
    └── actions_pipeline.sh     # Actions 里跑的完整流水线
```

本地运行时生成的 `data/`、`daily/`、`article/`、`*.html` 都已在 `.gitignore` 中忽略，
它们的正式副本保存在 `site-data` / `gh-pages` 分支上。

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

**工作流程**（`scripts/actions_pipeline.sh fetch`）：

1. 从 `site-data` 分支取回 `articles.jsonl`、`seen_urls.txt` 和已生成的精读页
2. 爬取各个来源的最新文章
3. 去重检查：URL 已存在于 `seen_urls.txt` 的跳过
4. 新文章追加进 `articles.jsonl`，同时按类型丢弃超出窗口的最旧记录
5. 自动调用 `process_original_articles.py` 处理新增原创文章
6. 调用 `rebuild_pages.py` 重新生成静态页面
7. 用 `build_site.py` 组装发布目录并推送到 `gh-pages`，数据回写 `site-data`

### 2. 原创文章处理

当你在 `original_articles/` 目录添加并提交了新的 `.md` 文件：

1. 下一次抓取任务会调用 `process_original_articles.py`
2. 扫描目录下所有 `.md` 文件
3. 提取标题（从一级标题）和摘要（前两段正文）
4. 使用 `markdown` 库将 Markdown 转换为 HTML
5. 使用预定义模板生成完整的文章详情页，保存到 `article/`
6. 将文章信息写入 `articles.jsonl`（`page_type = original`）
7. 详情页与数据一起推送到 `site-data`，页面进入 `gh-pages`

发布日期取该 Markdown 文件在 git 中的提交日期；文件未被 git 跟踪时才回退到修改时间，
这样同一篇文章在每次运行中都会得到相同的 URL，不会被重复入库。

### 3. 页面重建

`rebuild_pages.py` 做这些事情：

1. 从 `data/articles.jsonl` 按类型（tech/people/original）分别读取最新文章（按发布时间倒序，最多 1000 篇）
2. 使用 Jinja2 模板渲染三个列表页：
   - `tech-news.html` - 科技资讯
   - `people-news.html` - 时政观点
   - `articles.html` - 原创文章

### 4. 数据去重策略

- 爬取新闻：基于 URL 去重，历史 URL 永久保留在 `seen_urls.txt`
- 原创文章：基于生成的 URL 哈希去重，同一文件不会重复处理
- 每次重建页面都是全量重建，保证数据一致性

## 🗄️ 数据存放

`data/articles.jsonl` 每行一条 JSON 记录，字段与原来的 `news_articles` 表一致：

| 字段 | 说明 |
|------|------|
| id | 自增序号 |
| title | 文章标题（最长 500 字） |
| summary | 文章摘要 |
| url | 文章链接（去重键） |
| source | 来源 |
| publish_time | 发布时间 |
| author | 作者 |
| like_count / comment_count | 点赞数 / 评论数 |
| score | 排序分数（用于加权排序） |
| page_type | 页面类型：tech / people / original |

保留上限在 `scripts/store.py` 的 `KEEP_LIMIT` 里设置（tech 1500、people 3000、original 500），
刚好覆盖列表页的展示窗口，因此数据文件体积不会随时间增长。
2026 年 11 月之前的完整历史仍保存在旧服务器的数据库备份 `db/articles_migration.sql.gz` 中。

## 🎨 前端特性

- 🌓 **支持暗色/亮色主题切换** - 记住用户偏好
- 📱 **全响应式设计** - 完美适配桌面端和移动端
- ⚡ **纯静态HTML** - 加载速度极快，无需后端
- 🔍 **SEO友好** - 完整的 meta 标签和结构化数据
- 🎯 **分页加载** - 每页20篇，滚动自动加载更多

## 📝 如何添加原创文章

1. 在 `original_articles/` 目录新建 `.md` 文件
2. 编写 Markdown 内容，一级标题作为文章标题
   ```markdown
   # 文章标题

   这里是文章正文，会自动提取前两段作为摘要...

   ## 二级标题

   更多内容...
   ```
3. 提交并推送到 `main` 分支，下一次定时任务会自动处理；也可以手动触发
   `.github/workflows/fetch.yml`（Actions 页面的 "Run workflow"）
4. 网页自动更新完成 ✅

## 🔧 本地运行

GitHub Actions 是正式的运行环境，本地只需要在调试脚本时才运行。

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python scripts/fetch_news.py     # 抓取 + 重建页面
python scripts/rebuild_pages.py  # 只重建页面
```

本地产物在 `data/`、`daily/`、`article/` 与根目录的几个 `*.html`，均已被 `.gitignore` 忽略，
不会污染 `main` 分支。

### 密钥配置

仓库的 GitHub Actions 需要两个 Secret（Settings → Secrets and variables → Actions）：

| Secret | 用途 |
|--------|------|
| `LLM_API_KEY` | 调用百炼应用生成时评精读，缺省时脚本退回到规则分析 |

`GITHUB_TOKEN` 由 Actions 自动提供，工作流已声明 `permissions: contents: write`。

### GitHub Pages 设置

- Source：Deploy from a branch → 分支 `gh-pages`、目录 `/ (root)`
- Custom domain：`binjian.cloud`（由发布目录里的 `CNAME` 声明）
- Enforce HTTPS：勾选

## 📊 数据备份

站点内容与数据都在 `gh-pages` / `site-data` 分支上，随仓库一起由 GitHub 保存。
迁移前从旧服务器导出的完整数据库备份仍保留在本地 `db/` 目录（不进入公开仓库）。

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
