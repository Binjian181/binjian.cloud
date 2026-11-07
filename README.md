# binjian.cloud - 个人主页

这是我的个人主页，一个轻量级静态网站，集成了自动爬取资讯和原创文章管理功能。

🔗 在线访问：[https://binjian.cloud](https://binjian.cloud)

## 📋 项目概述

这是一个纯静态的个人网站，采用 Python 爬虫 + 文件数据存储 + Jinja2 模板渲染生成静态 HTML 的架构。
抓取、生成、发布全部由 GitHub Actions 完成，站点由 GitHub Pages 托管，不需要任何服务器或数据库。
内容分为五大板块：

- **🏠 首页** - 个人介绍和导航
- **📱 科技资讯** - 自动爬取少数派、36氪、澎湃新闻的最新科技文章
- **🇨🇳 时政观点** - 自动爬取人民网观点频道、浙江宣传的权威评论
- **📝 原创文章** - 我的原创文章，通过 Markdown 编写自动转换为 HTML
- **📖 时评精读** - 每日精选人民时评，逐段 AI 精读后存档

## 🛠️ 技术架构

三个分支各司其职，其中两个是单提交强制覆盖，因此仓库体积不会随时间增长：

```
┌──────────────────────────────────────────────────────┐
│  GitHub Actions                                      │
│  - fetch.yml      每 3 小时抓取资讯                  │
│  - daily-push.yml 北京时间 07:00 / 09:30 生成时评精读 │
│  两者共用 concurrency: site-pipeline，串行不互相打断  │
└───────────────────────────┬──────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐  ┌─────────────────┐  ┌──────────────────┐
│ main          │  │ site-data       │  │ gh-pages         │
│ 源码 + 生成页 │  │ 单提交，覆盖    │  │ 单提交，覆盖     │
│               │  │                 │  │                  │
│ scripts/      │  │ articles.jsonl  │  │ 站点根目录       │
│ templates/    │  │ seen_urls.txt   │  │ *.html css/ js/  │
│ css/ js/      │  │                 │  │ daily/ article/  │
│ daily/        │  │ 只有这两个数据  │  │ CNAME .nojekyll  │
│ article/      │  │ 文件            │  │                  │
│ index.html    │  │                 │  │ 不含脚本与数据   │
└───────────────┘  └─────────────────┘  └──────────────────┘
```

- `main` 保留完整提交历史，`daily/`（精读页）和 `article/`（原创页）作为成果跟踪在这里。
- `site-data` 只放文章数据和去重清单，每次运行整体覆盖，不累积历史。
- `gh-pages` 是 GitHub Pages 直接托管的目录，由 `build_site.py` 按白名单组装。

## 📁 目录结构

```
binjian.cloud/
├── index.html                  # 首页（手工维护）
├── profile.png / icons.png     # 头像与图标
├── css/ js/                    # 静态资源
├── templates/                  # Jinja2 模板
├── daily/                      # 时评精读页 + list.json（跟踪在 main）
├── article/                    # 原创文章详情页（跟踪在 main）
├── requirements.txt            # Actions 依赖清单
├── .github/workflows/
│   ├── fetch.yml               # 每 3 小时抓取并发布
│   └── daily-push.yml          # 每日时评精读
└── scripts/
    ├── store.py                # 文件型数据存储（替代 MySQL）
    ├── fetch_news.py           # 爬虫主流程
    ├── rebuild_pages.py        # 重建全部列表页（含 daily.html）
    ├── process_original_articles.py
    ├── daily_people_article_push_v3.py
    ├── build_site.py           # 按白名单组装发布目录
    └── actions_pipeline.sh     # Actions 里跑的完整流水线
```

`scripts/` 里另有若干历史遗留的一次性工具（CSS 迁移、数据迁移、批量补跑等），不参与日常流水线。

被 `.gitignore` 忽略的是**运行产物**：`data/`、根目录的 `tech-news.html` / `people-news.html` /
`articles.html` / `daily.html`，以及流水线临时目录 `.state/` / `.publish/`。
它们每次运行整体重写，正式副本在 `site-data` / `gh-pages` 分支上。
注意 `daily/` 和 `article/` **不在**忽略之列，它们是跟踪在 `main` 上的成果。

## 🔄 自动更新流程

### 1. 定时爬取新闻

由 `.github/workflows/fetch.yml` 驱动，cron `0 */3 * * *`（UTC，每 3 小时一次），
也可在 Actions 页面用 "Run workflow" 手动触发。

**爬取来源**：

| 来源 | 板块 | 说明 |
|------|------|------|
| 少数派 | 科技资讯 | 官方 API，自带点赞和评论数 |
| 36氪 | 科技资讯 | RSS |
| 澎湃新闻 | 科技资讯 | 科技频道列表 + 详情页 |
| 人民网观点频道 | 时政观点 | 爬取列表后进入详情页提取摘要 |
| 浙江宣传 | 时政观点 | 公众号文章列表 |

**流水线**（`scripts/actions_pipeline.sh fetch`，共 6 步）：

1. 从 `site-data` 分支取回 `articles.jsonl`、`seen_urls.txt` 到 `data/`
2. 执行抓取：新文章经 URL 去重后追加进 `articles.jsonl`，并按类型丢弃超出窗口的最旧记录；
   随后调用 `process_original_articles.py` 处理新增原创文章
3. **统一重建全部列表页**（`rebuild_pages.py`）
4. 把 `daily/`、`article/` 的变更提交回 `main`
5. 用 `build_site.py` 组装发布目录并强制推送到 `gh-pages`
6. 数据回写 `site-data`

第 3 步是必须的：列表页属于 gitignore 的运行产物，Actions 检出的仓库里没有它们，
而 fetch 和 daily 各自只重建一部分。统一重建才能保证任何一条流水线单独发布时站点都不缺页。
`build_site.py` 另有兜底——缺少任一必需页面就直接失败，绝不把残缺站点推上去。

### 2. 时评精读

由 `.github/workflows/daily-push.yml` 驱动，cron `0 23 * * *` 与 `30 1 * * *`（UTC），
即北京时间 07:00 与 09:30 各跑一次；第二次是兜底，用于处理清晨才发布、首轮没抓到的文章。
脚本会自动跳过已处理过的文章，因此重复运行是安全的。

流程：取最新一篇未处理的人民时评 → 清洗正文 → 调用阿里云百炼应用逐段精读 →
生成 `daily/YYYYMMDD_<hash>.html` → 更新 `daily/list.json` 并置顶当日文章 → 走同一条发布流水线。
未配置 `LLM_API_KEY` 时退回到规则分析。

### 3. 原创文章处理

当你提交新的 `.md` 文件到 `original_articles/` 后，下一次抓取任务会：

1. 扫描目录下所有 `.md` 文件
2. 提取标题（一级标题）和摘要（前两段正文）
3. 用 `markdown` 库转成 HTML，套用模板生成详情页保存到 `article/`
4. 将文章信息写入 `articles.jsonl`（`page_type = original`）
5. 详情页随 `article/` 提交到 `main`，再进入 `gh-pages`

发布日期取该文件在 git 中的提交日期，未被跟踪时才回退到修改时间，
这样同一篇文章每次运行都得到相同的 URL，不会重复入库。

> ⚠️ `original_articles/` 目录当前不存在，需要添加原创文章时自行新建。
> 早先的三篇原创文章因旧服务器重装丢失了 Markdown 源文件，只以生成好的 HTML 形式保存在 `article/` 中。

### 4. 页面重建

`rebuild_pages.py` 从 `data/articles.jsonl` 按类型读取最新文章（发布时间倒序，最多 1000 篇），
用 Jinja2 渲染四个页面：`tech-news.html`、`people-news.html`、`articles.html`，
以及从 `daily/list.json` 渲染的 `daily.html`。每次都是全量重建，保证一致性。

### 5. 去重策略

- 爬取新闻：基于 URL 去重，历史 URL 永久保留在 `seen_urls.txt`
- 原创文章：基于生成的 URL 哈希去重，同一文件不会重复处理

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

保留上限在 `scripts/store.py` 的 `KEEP_LIMIT` 中设置（tech 1500、people 3000、original 500），
覆盖列表页的展示窗口，因此数据文件体积稳定，不随时间增长。
迁移时已按此窗口裁剪，更早的历史文章不再保留在仓库中；`seen_urls.txt` 仍保留全部历史 URL，
所以被裁掉的文章不会被重新抓回来。

## 🎨 前端特性

- 🌓 **暗色/亮色主题切换** - 记住用户偏好，存在 localStorage
- 📱 **全响应式设计** - 适配桌面端和移动端
- ⚡ **纯静态 HTML** - 加载快，无需后端
- 🔍 **SEO 友好** - 完整的 meta 标签和结构化数据
- 🎯 **无限滚动** - 每页 20 篇，滚动自动加载更多
- 🎲 **随机跳转** - 原创文章详情页可随机滚动到任意位置，适合发现式阅读

## 📝 如何添加原创文章

1. 新建 `original_articles/` 目录（当前仓库里没有），在其中创建 `.md` 文件
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

GitHub Actions 是正式运行环境，本地只在调试脚本时才需要跑。
仓库里没有文章数据（在 `site-data` 分支上），调试前先取回：

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

mkdir -p data
git fetch origin site-data
git show FETCH_HEAD:articles.jsonl > data/articles.jsonl
git show FETCH_HEAD:seen_urls.txt  > data/seen_urls.txt

python scripts/rebuild_pages.py  # 只重建页面
python scripts/fetch_news.py     # 抓取 + 重建页面
```

本地产物均已被 `.gitignore` 忽略，不会污染 `main` 分支。
本地运行只写本地文件，不会推送任何分支——推送只发生在 Actions 里。

### 密钥配置

仓库只需要一个 Secret（Settings → Secrets and variables → Actions）：

| Secret | 用途 |
|--------|------|
| `LLM_API_KEY` | 调用百炼应用生成时评精读，缺省时脚本退回到规则分析 |

`GITHUB_TOKEN` 由 Actions 自动提供，两个工作流都已声明 `permissions: contents: write`。
本地调试若需 AI 精读，把 key 放进 gitignored 的 `.env.local`，不要写进任何跟踪文件。

### GitHub Pages 设置

- Source：Deploy from a branch → 分支 `gh-pages`、目录 `/ (root)`
- Custom domain：`binjian.cloud`（由发布目录里的 `CNAME` 声明）
- Enforce HTTPS：证书签发后勾选。证书由 GitHub 自动申请，DNS 生效后通常几十分钟内签发，
  官方口径最长 24 小时；若长时间未签发，可在 Settings → Pages 移除再重填自定义域名来强制触发。

## 🌐 域名解析

域名在 DNSPod 托管，解析指向 GitHub Pages：

| 记录 | 值 |
|------|-----|
| `@` A | `185.199.108.153`、`185.199.109.153` |
| `@` AAAA | `2606:50c0:8000::153`、`2606:50c0:8001::153` |
| `www` CNAME | `binjian181.github.io` |

GitHub 官方推荐 4 个 A / 4 个 AAAA 做冗余，但 DNSPod 免费套餐限制同一子域名同一类型最多 2 条
负载均衡记录（超出报 `LimitExceeded.SubdomainRollLimit`），因此各取前 2 个，不影响可用性。

## 📊 数据备份

站点内容与文章数据都在 GitHub 上：成果页在 `main`，文章数据在 `site-data`，
发布快照在 `gh-pages`，随仓库一起由 GitHub 保存，不需要额外备份任务。

## 📧 联系方式

- 网站：[https://binjian.cloud](https://binjian.cloud)
- 作者：张彬健 (Binjian)

## 📄 许可证

本项目仅供个人学习使用。
