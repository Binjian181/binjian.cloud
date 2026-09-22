# Design

<!-- impeccable:design-schema 1 · world=monyun-zhuyin seed=c0368a31 -->

> Visual world for binjian.cloud, written from the built surface (not before it). Replaces the
> incumbent indigo→purple→orange→pink gradient system.

## World

**墨韵·朱印** — an ink-and-paper Chinese editorial system drawn from 古籍 / 碑帖 / 印学
(classical books, stone rubbings, seal art). A calm reading room, not a portal. The single
committed accent is 朱砂 / 印泥红 (cinnabar vermilion); everything else is 宣纸 (paper) and 墨
(ink). The material discipline is pulled from the world's saturated roots — 朱丝栏 column rules,
印章 seal chips, 句读 vermilion marks — so it is not the generic "cream + serif + terracotta"
AI default.

- **Mode:** Read (readers come to read curated 精读). Color strategy: **Restrained** (neutrals + one accent).
- **Form:** replacement world, brief-pinned. The rolled catalog direction (seed `c0368a31`) was a
  whimsical physical metaphor unfit for a personal Chinese reading hub, so it was set aside on
  factual grounds per new-work; the user confirmed this direction.

## Palette

| Token | Light (宣纸) | Dark (夜色) | Role |
|---|---|---|---|
| `--bg-color` | `#f3ecdd` | `#16130d` | page ground |
| `--text-color` | `#211c15` | `#ece1cf` | 墨 ink |
| `--card-bg` | `#fbf6ea` | `#1f1a12` | panels / cards |
| `--border-color` | `#e2d7c2` | `#342d20` | hairlines |
| `--secondary-text` | `#6a5f4f` | `#b3a78e` | 淡墨 |
| `--muted-text` | `#9c9080` | `#8a7e69` | captions / meta |
| `--seal` / `--accent-color` | `#b1342b` | `#d9543f` | 朱砂 accent (only saturated color) |
| `--seal-soft` | `rgba(177,52,43,.10)` | `rgba(217,84,63,.16)` | 朱印 tint fields |
| `--on-seal` | `#fff` (6.2:1) | `#16130d` (4.67:1) | foreground on solid 朱砂 surfaces |
| `--rule` | `rgba(33,28,21,.14)` | `rgba(236,225,207,.16)` | 界栏 / 朱丝栏 hairline |

Gradients are removed everywhere; `--accent-gradient` is defined as a flat seal color only for
backward-compat with inline `var(--accent-gradient)` usages, which now render solid.

### Source-tag harmonized palette (印学)
Per-source chips keep recognizable distinct hues but are muted into the world: 人民网 → 朱砂
`--seal`; 少数派/sspai → 石青 `#3f5d7a`; 36氪 → 石绿 `#2f6f5b`; 澎湃 → 暖灰 `#6f6757`;
浙江宣传 → 紫泥 `#6b4a5c`（紫檀印泥，色相 327°，离其余四色最远）；原创 → 缃黄 (`--seal-soft` bg,
`--seal` text). Dark variants carry ink text on lightened grounds, all ≥4.5:1: 少数派 `#6689ac`
(5.06), 人民网 `#d75b4c` (4.85), 浙江宣传 `#9c7189`, 36氪 `#3f8d74`, 澎湃 `#8c8270`; 原创's
text lightens to `#e9795f` (5.5) because its tinted ground cannot deepen far enough (caps at 4.33).

Chip label and filter key both come from a display layer: `news_page.html` maps 浙江宣传 → 浙宣
via `source_labels`（仅展示，数据库与爬虫原值不动）, and filter keys are space-normalized
(`replace(' ','')`) so the 36氪 / "36 氪" DB variants collapse to one hue and one filter.

### Data-viz exception (documented, intentional)
`article/f6ba6edd.html` holds a reference comparison table (`.ref-table`) whose rows are
tier-coded — 最高规格 blue `#3b82f6`, 高规格 purple `#a855f7`, 中规格 green `#22c55e`,
特色栏目 yellow `#eab308` (each with dark-mode variants) — plus two header gradients. These are
**semantic tier discriminators**, not theme accents: collapsing them into a single 朱砂 ramp
would destroy the table's information function. Kept as a deliberate exception to the
single-accent rule — do not "correct" them back to 朱砂, and do not mistake them for the banned
indigo/purple/orange/pink gradient *themes* (a separate concern).

## Typography

- Reading face (headings, article body, summaries, 导语, markdown): CJK **宋体** stack —
  `'Songti SC','STSong','Source Han Serif SC','Noto Serif SC','SimSun',serif`. Deliberately
  *not* a named training-data display serif (Fraunces/Playfair/etc.); 宋体 is subject-appropriate.
- UI face (nav, meta, tags, footer): system sans — `-apple-system,'PingFang SC','Microsoft YaHei'`.
- No web fonts (Google Fonts blocked in CN); system stacks only.

## Material discipline (the raises from 印学)

- **朱批 top rule** — every `page-header` / hero panel carries a 3px `--seal` top border on a
  宣纸 card (replaces the white-on-gradient banner).
- **印章 active / badge** — `nav-btn.active` is a solid 朱砂 block (white text); the 精读
  `is-today` card carries a 朱印 (`--seal`) "今日更新" badge.
- **句读 / 朱批 block marks** — the 导语 (lead) and blockquotes carry a vermilion left rule
  (`--seal`); this is the one place a saturated side-rule is intentional (semantic emphasis, not
  card decoration). The impeccable detector's `side-tab` rule flags these; they are kept as a
  documented raise.
- **界栏 hover** — article cards are uniform-bordered; on hover the left edge turns 朱砂 (the
  朱丝栏 → 朱印 transition). Avoids the always-on colored side-border tell.
- **朱印签筛选栏** — `.source-filter` / `.filter-btn` (科技资讯 / 时政观点) are the 印章 language
  applied to a control: 宣纸 chip + hairline border, active = solid 朱砂 block (same as
  `nav-btn.active`); the row sits on a 界栏 hairline, not a floating glass panel. Foreground on
  solid 朱砂 is `--on-seal` — white in light (6.2:1), ink in dark (4.67:1, following the dark
  source-chip convention rather than the white-on-seal badge's 3.97:1). On narrow screens the row
  becomes a single-line horizontal strip whose edge fades appear only while chips overflow.

## Component language (cross-surface)

Driven entirely by `css/common.css` tokens. Templates (`news_page`, `articles_page`,
`daily`, `daily_detail`, `discussion_page`) and the crawler-generated article detail page
(`process_original_articles.py` → `ARTICLE_TEMPLATE`) no longer set per-section `--accent-*`
overrides or gradients; they inherit the unified world. `index.html` (standalone, not
crawler-regenerated) is restyled inline to match.

## Preserved quality floor

- Dark / light via `data-theme` on `<html>` + `localStorage` (`js/common.js` untouched).
- Responsive layout + mobile menu + theme toggle IDs preserved.
- SEO: JSON-LD Person/Article blocks kept in `daily.html`, `daily_detail.html`, `ARTICLE_TEMPLATE`.
- Behavior: infinite scroll, random-jump (`#randomJumpBtn`), back-to-top (`#backToTop`/`#backToTopBtn`)
  all preserved in `ARTICLE_TEMPLATE`.
- Identity: 张彬健 / Binjian name, `profile.png`, `icons.png`/`icons.svg` untouched.
- Cross-context adaptation (added via `/impeccable adapt`, all in `css/common.css`): `@media print` clean print/PDF export (white paper, black ink, 朱砂 top rule as brand mark, nav/footer/floating buttons/返回链接 hidden, source URLs expanded for traceability, sensible page breaks); touch/mouse split via `@media (hover: none)` (`:active` feedback instead of stuck hover) + `@media (pointer: coarse)` (≥44px tap targets on drawer nav / theme toggle / menu / source tags); `@media (max-width: 390px)` small-screen fallback (tightened spacing, `article-title` forced to 17px against the detail-page inline 22px).

## Provenance

- Tool: impeccable v4.1.2 (`pbakaus/impeccable`), new-work flow.
- Direction seed: `c0368a31` (rolled catalog world set aside as unfit; brief-pinned replacement).
- No raster assets were produced; the world is type/CSS-only, so no image provenance is owed.
- Finish: detected (web, degraded regex mode) → `common.css` clean; residual `side-tab` on
  semantic blockquote/导语 rules accepted as intentional raises.
- Refinement (2026-09-22, v4.3.1): 来源筛选栏 rebuilt from its ad-hoc inline style
  (glass panel + rounded pills + `#667eea` indigo fallback) into the world as 朱印签; added the
  `--on-seal` token and the single-line overflow strip. Detector vs the HEAD baseline: the old
  bar's real violation (`#fff on #667eea`, 3.7:1) is gone; the remaining findings are pre-existing
  raises (7× `side-tab` 朱批/导语 rules, `border-accent-on-rounded` on the 朱批 page-header) plus
  one cross-scope false positive — degraded regex mode pairs dark `--on-seal #16130d` with light
  `--seal #b1342b`, which never co-occur (each theme defines the pair together: 6.18:1 light,
  4.67:1 dark; the same mode also pairs the print-only tokens `#000 on #b1342b`).
- Refinement (2026-09-22, v4.3.1 · 来源签): 浙江宣传 chip added (紫泥 `#6b4a5c` light / `#9c7189`
  dark — it previously rendered with no chip at all). WCAG audit of every chip pair against the
  4.5:1 floor found three dark-mode failures, fixed under the fix-only-the-failing-values scope:
  two grounds lightened (人民网 `#cf4a3d` 4.15 → `#d75b4c` 4.85, 少数派 `#5a7da0` 4.30 → `#6689ac`
  5.06) and one text lightened (原创 3.95 → `#e9795f` 5.5, the tint-deepening route capping at
  4.33). Provenance gap noted, not fixed: dark chip variants key on `[data-theme="dark"]` only, so
  first-time system-dark visitors (no `data-theme` attribute) still get the light chips — they
  remain legible there, so this degrades gracefully; a `prefers-color-scheme` variant would be the
  fix if it ever matters. Cache note: the chip edits initially shipped under the unchanged
  `?v=20260922` and were invisible to anyone who had already loaded that URL (nginx `expires 1y`,
  and `.article-source` has no base background, so a missing rule = an invisible chip). All 190
  pages + templates + `ARTICLE_TEMPLATE` now point at `?v=20260922b`;
  **every `css/common.css` edit must bump the version via `/home/ubuntu/add_cache_version.py`**.
