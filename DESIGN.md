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
| `--rule` | `rgba(33,28,21,.14)` | `rgba(236,225,207,.16)` | 界栏 / 朱丝栏 hairline |

Gradients are removed everywhere; `--accent-gradient` is defined as a flat seal color only for
backward-compat with inline `var(--accent-gradient)` usages, which now render solid.

### Source-tag harmonized palette (印学)
Per-source chips keep recognizable distinct hues but are muted into the world: 人民网 → 朱砂
`--seal`; 少数派/sspai → 石青 `#3f5d7a`; 36氪 → 石绿 `#2f6f5b`; 澎湃 → 暖灰 `#6f6757`;
原创 → 缃黄 (`--seal-soft` bg, `--seal` text). Dark-mode variants provided.

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
