# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary user: the author (张彬健 / Binjian) himself — the site functions first as a personal reading archive and curation workspace.

Secondary audience: readers who discover the curated Chinese-language tech news, current-affairs opinions, original writing, and the daily deep-reads.

Situation / job: the author aggregates and re-reads content of interest (tech, opinion, own writing) in one calm, personal place; visitors browse curated feeds and the daily "精读" for signal over noise.

## Product Purpose

A lightweight personal homepage that auto-aggregates tech news (少数派, 36氪) and authoritative opinion (人民网观点频道), hosts the author's original articles, and publishes a daily hand-curated "精读" (deep-read) selection. It exists as a quiet, personal, non-commercial reading + curation hub.

## Positioning

The daily hand-curated "精读" deep-read is the distinct edge — human selection and framing on top of aggregated feeds, plus the author's own original commentary. It is deliberately not a generic aggregator or a commercial portal.

## Operating Context

- Python crawler (fetch_news.py, process_original_articles.py, rebuild_pages.py, etc.) + MySQL + Jinja2 templates render static HTML, served by Nginx.
- Crawler runs every 3h via crontab; `rebuild_pages.py` regenerates list/detail pages from the DB on each run.
- Design changes MUST live in `templates/` and `css/common.css`. Generated HTML (`index.html`, `tech-news.html`, `people-news.html`, `articles.html`, `daily.html`, `article/*`) is overwritten on every rebuild — never edit generated HTML directly or the crawler will clobber it.
- Theme preference is persisted in localStorage; the site supports dark/light.

## Capabilities and Constraints

- Confirmed functionality: dark/light theme toggle (persisted), full responsive layout, SEO meta + structured data, infinite scroll (20 items/page), random-jump within article detail, Markdown→HTML for originals.
- Technical constraints: pure static at runtime (no backend); the content lifecycle is owned by the crawler + DB; design edits must stay in `templates/` + `css/`.
- Undecided: specific visual direction — explicitly delegated to design work (see Brand Commitments).

## Brand Commitments

- Personal, non-commercial tone and spirit must be preserved (license: 个人学习使用).
- Author identity assets exist and should be kept as identity: name 张彬健 / Binjian, `profile.png`, `icons.png`, `icons.svg`. Do not drop or invent identity.
- Visual direction is NOT constrained: free to redesign (user-stated, 2026-08-28). The incumbent dark/light, responsive, and SEO behaviors are preserved as a quality floor, not as a style lock.
- **Established visual world (2026-08-28):** "墨韵·朱印" — ink-and-paper Chinese editorial system (宣纸 ground, 墨 ink, single 朱砂/印泥红 accent, 宋体 reading face). Documented in `DESIGN.md`. Per-section gradient themes (the old indigo/purple/orange/pink) were replaced and must not return; design edits stay in `templates/` + `css/common.css` + `process_original_articles.py`'s `ARTICLE_TEMPLATE`.

## Evidence on Hand

- `README.md` (architecture + feature list).
- `templates/` (base.html, news_page.html, daily.html, daily_detail.html, articles_page.html, discussion_page.html).
- `css/common.css`, `js/common.js`.
- Crawler scripts in `/home/ubuntu/` (fetch_news.py, process_original_articles.py, rebuild_pages.py, daily_people_article_push_v3.py, batch_generate_daily.py, fix_daily_lead_paragraphs.py).
- Author: 张彬健 (Binjian). Site: https://binjian.cloud.
- Absent: no `DESIGN.md` yet (incumbent visual system is undocumented); no `PRODUCT.md` before this file.

## Product Principles

1. Personal and non-commercial: a quiet reading/curation space, not a growth-optimized portal.
2. Human curation over raw aggregation — the daily "精读" is the soul of the site.
3. Calm, legible, content-first; respect the reader's attention.
4. Preserve the incumbent quality floor: responsive, accessible, SEO, dark/light.
5. Design serves the content and never breaks the crawler-driven build.

## Accessibility & Inclusion

No formal WCAG requirement stated. Maintain responsive layout, legible typography, and sufficient contrast (including in dark mode); keep the site usable across desktop and mobile.
