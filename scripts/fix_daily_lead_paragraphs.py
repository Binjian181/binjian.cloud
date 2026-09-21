#!/usr/bin/env python3
"""
批量修复 daily/ 目录下所有文章的导语识别和总段落数统计问题。

修复内容：
1. 重新解析每篇 HTML 中的所有段落（导语 + 正文）
2. 用 is_lead_paragraph 规则重新判断连续多段导语
3. 重新渲染 HTML 文件（替换正文全文区块 + 文章数据统计区块）
4. 更新 list.json 中的 para_count（仅统计正文段落，不含导语）
"""

import os
import re
import json
from bs4 import BeautifulSoup

DAILY_DIR = '/var/www/binjian.cloud/daily'
LIST_FILE = os.path.join(DAILY_DIR, 'list.json')


def is_lead_paragraph(para: str) -> bool:
    para = para.strip()
    if not para:
        return False
    last_char = para[-1]
    return last_char not in '。！？.'


def extract_all_paragraphs_from_html(html_path: str):
    """
    从已生成的 HTML 中提取所有段落（导语段落 + 正文段落），
    恢复为原始顺序的完整段落列表。
    返回 (lead_paras, body_paras) 两个列表。
    """
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    fulltext = soup.select_one('.fulltext-content')
    if not fulltext:
        return [], []

    # 提取现有导语段落文本
    lead_paras = []
    lead_div = fulltext.select_one('.lead-paragraph')
    if lead_div:
        lead_label = lead_div.select_one('.lead-label')
        if lead_label:
            lead_label.decompose()
        raw = lead_div.get_text('\n', strip=True)
        # 导语可能是多段，按换行拆分
        for line in raw.split('\n'):
            line = line.strip()
            if line:
                lead_paras.append(line)

    # 提取正文段落（para-text）
    body_paras = []
    for item in fulltext.select('.paragraph-item'):
        para_text_div = item.select_one('.para-text')
        if para_text_div:
            text = para_text_div.get_text(strip=True)
            if text:
                body_paras.append(text)

    return lead_paras, body_paras


def recheck_lead(lead_paras, body_paras):
    """
    把所有段落合并后，重新用 is_lead_paragraph 规则判断导语。
    原来误判为正文的导语段落会被归回导语；
    原来误判为导语的正文段落会被归入正文。
    返回 (new_lead_paras, new_body_paras)
    """
    all_paras = lead_paras + body_paras

    new_lead = []
    for para in all_paras:
        if is_lead_paragraph(para):
            new_lead.append(para)
        else:
            break

    new_body = all_paras[len(new_lead):]
    return new_lead, new_body


def build_fulltext_html(lead_paras, body_paras) -> str:
    """重新构建 .fulltext-content 内部的 HTML"""
    lines = []

    if lead_paras:
        lead_text = '<br><br>'.join(lead_paras)
        lines.append('            <div class="lead-paragraph">')
        lines.append('                <div class="lead-label">📌 导语</div>')
        lines.append(f'                {lead_text}')
        lines.append('            </div>')

    for i, para in enumerate(body_paras, start=1):
        lines.append('            <div class="paragraph-item">')
        lines.append(f'                <span class="para-num">{i}</span>')
        lines.append(f'                <div class="para-text">{para}</div>')
        lines.append('            </div>')

    return '\n'.join(lines)


def fix_html_file(html_path: str) -> tuple:
    """
    修复单篇 HTML。
    返回 (changed: bool, old_body_count: int, new_body_count: int,
           old_lead_count: int, new_lead_count: int)
    """
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    soup = BeautifulSoup(content, 'html.parser')
    fulltext = soup.select_one('.fulltext-content')
    if not fulltext:
        return False, 0, 0, 0, 0

    lead_paras, body_paras = extract_all_paragraphs_from_html(html_path)
    new_lead, new_body = recheck_lead(lead_paras, body_paras)

    old_lead_count = len(lead_paras)
    new_lead_count = len(new_lead)
    old_body_count = len(body_paras)
    new_body_count = len(new_body)

    changed = (old_lead_count != new_lead_count) or (old_body_count != new_body_count)

    # 多段导语但导语 div 里还没有 <br><br> 分隔，也需要修复
    if not changed and new_lead_count > 1:
        lead_div = fulltext.select_one('.lead-paragraph') if fulltext else None
        if lead_div and '<br>' not in str(lead_div):
            changed = True

    if not changed:
        # 即使段落数没变，也检查并修复「总段落数」统计是否包含了导语
        # 找 stats 区块里的 total_paras 显示值
        stat_badges = soup.select('.stat-badge')
        for badge in stat_badges:
            text = badge.get_text()
            if '总段落数' in text:
                m = re.search(r'(\d+)', badge.find('strong').get_text() if badge.find('strong') else '')
                if m and int(m.group(1)) != new_body_count:
                    changed = True
                break

    if not changed:
        return False, old_body_count, new_body_count, old_lead_count, new_lead_count

    # ---- 替换 .fulltext-content 内容 ----
    new_fulltext_inner = build_fulltext_html(new_lead, new_body)

    # 用字符串替换（BeautifulSoup 会破坏 Jinja 转义，改用正则）
    # 匹配 <div class="fulltext-content"> ... </section> 之间的内容
    pattern = r'(<div class="fulltext-content">)([\s\S]*?)(</div>\s*</section>)'

    def replace_fulltext(m):
        return m.group(1) + '\n' + new_fulltext_inner + '\n        ' + m.group(3)

    new_content = re.sub(pattern, replace_fulltext, content, count=1)

    # ---- 替换总段落数统计 ----
    # 匹配 <span class="stat-badge">📄 总段落数：<strong>N</strong></span>
    new_content = re.sub(
        r'(<span class="stat-badge">📄 总段落数：<strong>)\d+(</strong></span>)',
        rf'\g<1>{new_body_count}\g<2>',
        new_content
    )

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return True, old_body_count, new_body_count, old_lead_count, new_lead_count


def fix_list_json(url_to_new_count: dict):
    """更新 list.json 中对应文章的 para_count"""
    if not url_to_new_count:
        return
    with open(LIST_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f)

    updated = 0
    for article in articles:
        url = article.get('url', '')
        if url in url_to_new_count:
            old = article.get('para_count', '?')
            article['para_count'] = url_to_new_count[url]
            updated += 1

    with open(LIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f'\n✅ list.json 已更新（{updated} 篇）')


def main():
    print('=' * 60)
    print('批量修复导语识别 & 总段落数统计')
    print('=' * 60)

    html_files = sorted([
        f for f in os.listdir(DAILY_DIR)
        if f.endswith('.html')
    ])

    url_to_new_count = {}
    changed_count = 0

    for fname in html_files:
        fpath = os.path.join(DAILY_DIR, fname)
        changed, old_body, new_body, old_lead, new_lead = fix_html_file(fpath)
        url = f'/daily/{fname}'

        if changed:
            changed_count += 1
            url_to_new_count[url] = new_body
            print(f'[修复] {fname}')
            if old_lead != new_lead:
                print(f'       导语段数: {old_lead} → {new_lead}')
            if old_body != new_body:
                print(f'       正文段数: {old_body} → {new_body}（总段落数已更新）')
        else:
            # 即使没改 HTML，也同步 list.json 里的 para_count
            url_to_new_count[url] = new_body

    print(f'\n共修复 {changed_count} 篇（共 {len(html_files)} 篇）')

    # 同步所有文章的 para_count 到 list.json（包括未变动的，确保一致）
    # 重新读取所有文件的正文段落数
    print('\n正在同步 list.json 中的 para_count...')
    url_to_correct_count = {}
    for fname in html_files:
        fpath = os.path.join(DAILY_DIR, fname)
        lead_paras, body_paras = extract_all_paragraphs_from_html(fpath)
        _, new_body = recheck_lead(lead_paras, body_paras)
        url_to_correct_count[f'/daily/{fname}'] = len(new_body)

    fix_list_json(url_to_correct_count)

    print('\n完成！')


if __name__ == '__main__':
    main()
