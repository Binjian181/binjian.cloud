#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段 2/3 视觉零变化验证：逐元素比对计算样式。

做法：对每个 URL，准备两个版本
  基线版 = /tmp/binjian_baseline_20260829 下的原样页面（带内联 <style>）
  新版   = 去掉内联 <style> 的同名页面 + 新的 css/common.css
两者用同一份 DOM（基线 DOM 剥掉 <style> 即得新版 DOM），
因此逐元素逐个属性的计算样式必须完全一致。

指标：18 个高频视觉属性 × 全部元素 × 亮/暗两主题。
有任何差异即判定为迁移有遗漏。
"""
import functools
import http.server
import re
import shutil
import socket
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

SITE = Path('/var/www/binjian.cloud')
BASE = Path('/tmp/binjian_baseline_20260829')
WORK = Path('/tmp/verify_stage2')

PROPS = ['display', 'position', 'float', 'flex', 'fontFamily', 'fontSize', 'fontWeight',
         'lineHeight', 'textAlign', 'color', 'backgroundColor', 'borderTopWidth',
         'borderTopColor', 'borderRadius', 'margin', 'padding', 'width', 'height',
         'boxShadow', 'opacity', 'zIndex', 'letterSpacing', 'overflowWrap', 'tableLayout']

PROPS += ['textDecorationLine', 'whiteSpace', 'maxWidth', 'minWidth', 'flexDirection',
          'justifyContent', 'alignItems', 'gap', 'transform', 'overflowX', 'visibility']


def strip_inline_styles(html):
    """删掉页面内的 <style>…</style>（保留 <link> 等其他一切）。

    注意：块内不能跨越 </style>，否则会把夹在中间的 <link rel=stylesheet> 一起删掉
    —— 首版就踩了这个坑，导致新版页面完全没有 CSS。"""
    return re.sub(r'[ \t]*<style>(?:(?!</style>).)*</style>\n?', '', html, flags=re.S | re.M)


def prepare():
    """构建工作目录：base/ 为原样，new/ 为剥离内联版（共用新 common.css）。"""
    if WORK.exists():
        shutil.rmtree(WORK)
    (WORK / 'base').mkdir(parents=True)
    (WORK / 'new').mkdir(parents=True)

    # 挑一篇 daily 作为样本
    sample = sorted((BASE / 'daily').glob('*.html'))[0].name

    targets = [
        'index.html',
        'daily/' + sample,
        'article/78a28fa0.html',
        'article/f6ba6edd.html',   # 孤儿页：携带 200 行孤儿样式，必须验
        'article/a6704eb4.html',
        'tech-news.html',
        'people-news.html',
    ]
    for rel in targets:
        src = BASE / rel
        html = src.read_text(encoding='utf-8')
        # 基线版：内联样式保留，但 CSS 指向工作目录里的新 common.css
        (WORK / 'base' / rel).parent.mkdir(parents=True, exist_ok=True)
        (WORK / 'base' / rel).write_text(html, encoding='utf-8')
        # 新版：剥掉内联样式
        (WORK / 'new' / rel).parent.mkdir(parents=True, exist_ok=True)
        (WORK / 'new' / rel).write_text(strip_inline_styles(html), encoding='utf-8')

    # 两侧共用同一份新 common.css（同一份，才能验证内联是否已被完全吸收）
    for side in ('base', 'new'):
        (WORK / side / 'css').mkdir(exist_ok=True)
        shutil.copy(SITE / 'css/common.css', WORK / side / 'css/common.css')
    return sample


JS = """(cfg) => {
  const props = cfg.props, ignore = cfg.ignore;
  const out = [];
  // <style>/<script> 本身不参与渲染，且新版已剥掉 <style>，必须排除
  const SKIP = new Set(['style', 'script', 'head', 'meta', 'link', 'title', 'noscript']);
  const walk = (el, path, ignored) => {
    const tag = el.tagName.toLowerCase();
    // ignored：自身或子孙命中「已知刻意的视觉变更」（如阶段 1 的分级色降饱和）。
    // 祖先也要连带跳过 height —— 高度会因子孙变化而传导。
    const isIgnored = ignored || (ignore && el.matches && el.matches(ignore));
    if (!SKIP.has(tag)) {
      const cs = getComputedStyle(el);
      const rec = {path, props: {}, ign: isIgnored};
      for (const p of props) rec.props[p] = cs[p];
      out.push(rec);
    }
    const kids = el.children;
    for (let i = 0; i < kids.length; i++) {
      const k = kids[i], kt = k.tagName.toLowerCase();
      if (SKIP.has(kt)) continue;
      walk(k, path + ' > ' + kt +
           (k.className && typeof k.className === 'string'
            ? '.' + k.className.trim().split(/\\s+/).join('.') : ''), isIgnored);
    }
  };
  walk(document.body, 'body', false);
  return out;
}"""


def serve(directory):
    """起一个本地 HTTP 服务 —— 页面里的 /css/common.css 是绝对路径，file:// 下解析不到。"""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    handler.log_message = lambda *a, **k: None
    for port in range(8900, 8950):
        try:
            httpd = http.server.ThreadingHTTPServer(('127.0.0.1', port), handler)
            break
        except OSError:
            continue
    else:
        sys.exit('找不到可用端口')
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, 'http://127.0.0.1:%d' % port


def collect(page, url, props=PROPS, ignore=None):
    page.goto(url, wait_until='load')
    recs = page.evaluate(JS, {'props': props, 'ignore': ignore or ''})
    # 标记「被忽略元素的祖先」：它们的 height 会因子孙的刻意变更而传导，比对时跳过 height
    ignored_paths = [r['path'] for r in recs if r.get('ign')]
    for r in recs:
        r['ignAnc'] = any(p.startswith(r['path'] + ' > ') for p in ignored_paths)
    return recs


def main():
    sample = prepare()
    # （名称, 相对路径, 刻意变更的选择器——命中者及其祖先的 height 一并跳过）
    # 孤儿页的阶段 1 分级色 + 速查表窄屏横向滚动，都是刻意的视觉变更
    TIER = ('.tier-badge, .ref-table, .ref-table *, .ref-legend-dot, .ref-table-wrap, '
            '.back-to-top')
    pages = [
        ('首页', 'index.html', None),
        ('时评精读详情', 'daily/' + sample, None),
        ('原创文章详情 78a28fa0', 'article/78a28fa0.html', TIER),
        ('原创孤儿页 f6ba6edd', 'article/f6ba6edd.html', TIER),
        ('原创文章 a6704eb4', 'article/a6704eb4.html', TIER),
        ('列表 tech-news', 'tech-news.html', None),
        ('列表 people-news', 'people-news.html', None),
    ]

    # base/ 与 new/ 各起一个服务，两侧都用自己的 CSS 副本（内容相同）
    httpd_base, base_url = serve(WORK / 'base')
    httpd_new, new_url = serve(WORK / 'new')
    print('服务已启动：base=%s  new=%s' % (base_url, new_url))

    total_diff = 0
    with sync_playwright() as p:
        # 环境里没有 playwright 自带的 chromium，改用系统安装的 Chrome
        browser = p.chromium.launch(executable_path='/usr/bin/google-chrome',
                                    args=['--no-sandbox'])
        for theme in ('light', 'dark'):
            for vw in (1280, 375):          # 桌面 + 窄屏（触发响应式规则）
                ctx = browser.new_context(color_scheme=theme,
                                          viewport={'width': vw, 'height': 900})
                page = ctx.new_page()
            for name, rel, ignore in pages:
                a = collect(page, '%s/%s' % (base_url, rel), ignore=ignore)
                b = collect(page, '%s/%s' % (new_url, rel), ignore=ignore)
                if len(a) != len(b):
                    print('  ❌ %s [%s] 元素数不一致：基线 %d vs 新版 %d'
                          % (name, theme, len(a), len(b)))
                    total_diff += 1
                    continue
                diffs = []
                for ra, rb in zip(a, b):
                    if ra['path'] != rb['path']:
                        diffs.append(('结构不一致', ra['path'], rb['path']))
                        continue
                    # 被忽略的元素（刻意的视觉变更）整条跳过
                    if ra.get('ign') or rb.get('ign'):
                        continue
                    # 其祖先只跳过 height —— 高度会因子孙变化而传导
                    skip = {'height'} if (ra.get('ignAnc') or rb.get('ignAnc')) else set()
                    for prop in PROPS:
                        if prop in skip:
                            continue
                        va, vb = ra['props'].get(prop), rb['props'].get(prop)
                        if va != vb:
                            diffs.append((ra['path'], prop, va, vb))
                if diffs:
                    total_diff += len(diffs)
                    print('  ❌ %s [%s/%dpx] %d 处差异（元素 %d）：'
                          % (name, theme, vw, len(diffs), len(a)))
                    for d in diffs[:12]:
                        print('       ', d)
                    if len(diffs) > 12:
                        print('        ... 另有 %d 处' % (len(diffs) - 12))
                else:
                    print('  ✅ %s [%s/%dpx] %d 元素 × %d 属性 完全一致'
                          % (name, theme, vw, len(a), len(PROPS)))
            ctx.close()
        browser.close()

    print()
    print('总计差异：', total_diff)
    sys.exit(1 if total_diff else 0)


if __name__ == '__main__':
    main()
