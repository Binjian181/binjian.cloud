#!/usr/bin/env python3
"""
每日人民网评论推送脚本 V3（AI 分析版 - 异步处理）
功能：
1. 清理正文（去除作者、时间、来源、责编等）
2. 逐篇传给 AI 应用
3. 等待 2 分钟，未完成则每分钟检测一次
4. 根据 AI 返回格式优化网页排版
"""

import sys
import os
import requests
import pymysql
from bs4 import BeautifulSoup
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import json
import hashlib
import time
from typing import List, Dict, Tuple, Optional

# DashScope SDK for Bailian
try:
    import dashscope
    from dashscope import Application
    BAILIAN_AVAILABLE = True
except ImportError:
    BAILIAN_AVAILABLE = False
    print("⚠️  未安装 DashScope SDK")

# ==================== 配置区域 ====================

BASE_CONFIG = {
    'output_dir': '/var/www/binjian.cloud',
    'templates_dir': '/var/www/binjian.cloud/templates',
    'retry_times': 3,
    'retry_delay': 2,
}

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': '19930107ZBj',
    'database': 'articles',
    'charset': 'utf8mb4',
}

AI_CONFIG = {
    'enabled': True,
    'api_key': 'sk-ws-H.ERRMEML.y1fD.MEUCIQCzkMj80eh66900ACXhH0lFZCpeilFu21HPGkMr8N5rfQIgJbaifsgEEmzqLQx_B0tq_cH7PA0hIkcr8GpOYYDj3n8',
    'app_id': '1f605f0d7f89470d83a3c623f6eaeeb5',
    'wait_time_initial': 120,  # 首次等待 2 分钟
    'wait_time_retry': 60,     # 重试等待 1 分钟
    'max_wait_count': 10,      # 最多等待 10 次
}

# 需要过滤的内容关键词
FILTER_KEYWORDS = [
    '人民日报', '人民网', '责编', '责任编辑', '来源：', '作者：',
    '更新时间', '发表版面', '本版责编', '版编', '校对',
    '人 民 网', '版权所有', '许可证号', '举报中心',
    # 许可证相关信息
    '互联网新闻信息服务许可证', '增值电信业务经营许可证', '广播电视节目制作经营许可证',
    '京ICP备', 'ICP备', '（广媒）字',
]

# ==================== 数据库操作 ====================

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

def get_latest_unprocessed_article() -> Optional[Dict]:
    """获取最新一篇未处理的文章（优先选最新的，无新文章时从库里逆日期选未精读的）"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor=pymysql.cursors.DictCursor) as cursor:
            # 查询所有人民时评文章，按发布时间降序
            # 注意：publish_time为空的排到最后，避免选到没有日期的文章
            sql = """
                SELECT id, title, url, source, publish_time 
                FROM news_articles 
                WHERE page_type = 'people' AND source = '人民网'
                AND title LIKE '%（人民时评）%'
                ORDER BY 
                    CASE WHEN publish_time IS NULL OR publish_time = '' THEN 1 ELSE 0 END,
                    publish_time DESC, id DESC
            """
            cursor.execute(sql)
            articles = cursor.fetchall()
        
        processed_urls = get_processed_article_urls()
        skipped_urls = get_skipped_article_urls()
        
        # 按日期逆序遍历，选第一篇未处理的
        for article in articles:
            if article['url'] not in processed_urls and article['url'] not in skipped_urls:
                if is_valid_article(article):
                    return article
        
        print("⚠️  所有人民时评文章都已处理过")
        return None
    finally:
        conn.close()

def get_processed_article_urls() -> set:
    list_file = os.path.join(BASE_CONFIG['output_dir'], 'daily', 'list.json')
    if not os.path.exists(list_file):
        return set()
    try:
        with open(list_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        return {article.get('original_url', '') for article in articles if article.get('original_url')}
    except:
        return set()

def get_skipped_article_urls() -> set:
    skipped_file = os.path.join(BASE_CONFIG['output_dir'], 'daily', 'skipped.json')
    if not os.path.exists(skipped_file):
        return set()
    try:
        with open(skipped_file, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    except:
        return set()

def is_valid_article(article: Dict) -> bool:
    title = article.get('title', '')
    if len(title) > 50:
        return False
    exclude_keywords = ['快讯', '直播', '视频', '图集', '预告', '招聘', '广告']
    for keyword in exclude_keywords:
        if keyword in title:
            return False
    return True

# ==================== 内容爬取与清理 ====================

def get_and_clean_article(url: str) -> Tuple[List[str], str]:
    """
    获取文章内容并清理无关信息
    
    Returns:
        (清理后的段落列表，原始 URL)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    print(f"\n📖 正在获取并清理文章内容：{url}")
    
    try:
        # 转换为 http
        if url.startswith('https://'):
            url = url.replace('https://', 'http://')
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        html = response.content.decode('UTF-8', errors='replace')
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找正文区域
        content_selectors = ['#rm_txt_zw', '#rwb_zw', '.article-content', '.text', '.content']
        content_elem = None
        for selector in content_selectors:
            elem = soup.select_one(selector)
            if elem and len(elem.get_text().strip()) > 200:
                content_elem = elem
                break
        
        if not content_elem:
            content_elem = soup.body
        
        # 提取段落并过滤
        paragraphs = []
        
        for p in content_elem.find_all('p'):
            text = p.get_text().strip()
            
            # 过滤掉太短的段落
            if len(text) < 10:
                continue
            
            # 过滤掉包含关键词的段落（作者、时间、来源等）
            if any(keyword in text for keyword in FILTER_KEYWORDS):
                continue
            
            # 过滤掉纯数字或特殊符号
            if re.match(r'^[\d\s\-\(\)]+$', text):
                continue
            
            paragraphs.append(text)
        
        # 如果还是没有段落，尝试直接提取文本
        if not paragraphs:
            text = content_elem.get_text('\n', strip=True)
            raw_paragraphs = [p.strip() for p in text.split('\n') if len(p.strip()) > 20]
            
            for p in raw_paragraphs:
                if not any(keyword in p for keyword in FILTER_KEYWORDS):
                    paragraphs.append(p)
        
        # 最后清理：确保第一段不是来源信息
        cleaned_paragraphs = []
        for i, para in enumerate(paragraphs):
            # 跳过开头可能遗漏的来源信息
            if i == 0 and any(k in para for k in ['来源', '作者', '记者', '人民网']):
                continue
            # 跳过结尾的版面信息
            if i == len(paragraphs) - 1 and any(k in para for k in ['版', '责编', '校对']):
                continue
            cleaned_paragraphs.append(para)
        
        print(f"✅ 清理后提取到 {len(cleaned_paragraphs)} 个段落")
        total_words = sum(len(p) for p in cleaned_paragraphs)
        print(f"   总字数：{total_words}")
        
        return cleaned_paragraphs, url
        
    except Exception as e:
        print(f"❌ 获取失败：{e}")
        return [], url

# ==================== AI 分析器（异步处理） ====================

class BailianAsyncAnalyzer:
    """阿里云百炼 AI 异步分析器"""
    
    def __init__(self):
        self.config = AI_CONFIG
        if not BAILIAN_AVAILABLE or not self.config['enabled']:
            print("⚠️  AI 分析未启用")
            return
        
        try:
            dashscope.api_key = self.config['api_key']
            print("✅ 阿里云百炼 AI 分析已启用")
        except Exception as e:
            print(f"⚠️  AI 初始化失败：{e}")
    
    def analyze_article_async(self, title: str, paragraphs: List[str]) -> Optional[str]:
        """
        异步提交 AI 分析任务
        
        Returns:
            task_id 或 None
        """
        if not BAILIAN_AVAILABLE or not self.config['enabled']:
            return None
        
        try:
            prompt = self._build_prompt(title, paragraphs)
            
            # 异步调用（不等待结果）
            response = Application.call(
                app_id=self.config['app_id'],
                prompt=prompt,
                session_id=None,
                incremental_output=False  # 完整输出
            )
            
            if response.status_code == 200:
                # 检查是否已有结果
                if response.output.text:
                    print("✅ AI 立即返回了结果")
                    return response.output.text
                else:
                    print("⏳ AI 正在处理中，需要等待...")
                    return None
            else:
                print(f"❌ API 调用失败：{response.code} - {response.message}")
                return None
                
        except Exception as e:
            print(f"❌ API 错误：{e}")
            return None
    
    def _build_prompt(self, title: str, paragraphs: List[str]) -> str:
        """构建 AI 分析提示词（使用用户应用中的专业提示词）"""

        # 组合正文内容
        article_text = "\n\n".join(paragraphs)

        prompt = f"""# Role: 资深党报评论编辑兼写作教练

# Profile:
你是一位拥有数十年经验的资深党报评论编辑，擅长撰写和解析时政评论文章。你深谙《人民日报》评论部的写作规范与审美标准，能够精准捕捉文章的核心观点、逻辑架构与修辞亮点。你的分析风格专业、深刻、具有指导性，能够透过文字表面看到文章的立意高度与现实针对性。

# Goal:
用户将提供一篇时政评论或时评文章。你需要为该文章撰写【佳句】选取和【解析】点评。

# Constraints & Style Guide:
1. **语气风格**：专业、客观、insightful（有洞察力）、建设性。使用党报评论分析的专业术语（如：顶层设计、基层实践、辩证统一、舆论引导、切入点、逻辑闭环等）。
2. **格式要求**：严格遵循以下 Markdown 格式输出，不得随意增减标题。
3. **内容深度**：解析不能流于表面，必须结合文章的政治站位、逻辑结构、素材运用和现实意义进行多维度剖析。

# Workflow:

## 1. 提炼【论点】
- **中心论点**：用 1 句话概括文章的核心主张
- **分论点**：列出文章的 2-4 个分论点（如有）
- **立意高度**：说明文章的政治站位和时代背景

## 2. 梳理【结构】
- **结构类型**：判断文章采用的结构（如：总 - 分 - 总、递进式、并列式、对比式等）
- **结构图示**：用文字或简单图示展示文章的论证脉络
- **过渡技巧**：分析段落之间如何衔接过渡

## 3. 选取【佳句】
- **数量**：严格选取 3 句。
- **标准**：
    - **句 1（核心论点）**：能概括文章中心思想或方法论的句子。
    - **句 2（修辞金句）**：善用对仗、排比、比喻，具有节奏感和记忆点的句子。
    - **句 3（价值升华）**：具有号召力、情感共鸣或政治高度的结尾句/关键句。
- **注意**：必须是原文原句，不可改写。

## 4. 撰写【解析】
- **字数**：300-500 字左右。
- **结构**（请涵盖以下 5 个维度，可融合撰写）：
    1. **立意与选题**：文章围绕什么主题？切入点在哪里？政治站位如何？（关键词：切入点、突破口、时代背景）
    2. **逻辑与结构**：文章是如何论证的？（关键词：层层递进、总 - 分 - 总、辩证关系、逻辑闭环）
    3. **素材与论证**：用了什么案例？效果如何？（关键词：以小见大、一线素材、针对性、说服力）
    4. **语言与风格**：文字质感如何？（关键词：烟火气、节奏感、政治性与文学性平衡）
    5. **价值与效果**：文章起到了什么作用？（关键词：舆论引导、方法论指导、入脑入心、现实意义）

以下是需要分析的人民时评正文：
<人民时评正文>
标题：{title}

{article_text}
</人民时评正文>

请按以下格式输出分析结果：

## 【论点】

**中心论点：**
[用 1 句话概括]

**分论点：**
1. [分论点 1]
2. [分论点 2]
3. [分论点 3]（如有）

**立意高度：**
[说明政治站位和时代背景]

## 【结构】

**结构类型：**
[如：总 - 分 - 总、递进式、并列式等]

**结构图示：**
[用文字或符号展示论证脉络，例如：开篇引入 → 论点提出 → 分论点 1 → 分论点 2 → 分论点 3 → 结尾升华]

**过渡技巧：**
[分析段落衔接方式]

## 【佳句】

1. [句子 1]
2. [句子 2]
3. [句子 3]

## 【解析】

[在此处撰写解析内容，分段或连贯撰写均可，但需涵盖上述 5 个维度，保持专业点评风格]"""

        return prompt
    
    def wait_for_result(self, title: str, paragraphs: List[str], max_count: int = None) -> Optional[Dict]:
        """
        等待 AI 分析结果
        
        Args:
            title: 文章标题
            paragraphs: 段落列表
            max_count: 最大等待次数
        
        Returns:
            分析结果字典或 None
        """
        if max_count is None:
            max_count = self.config['max_wait_count']
        
        print(f"\n🤖 开始等待 AI 分析结果...")
        print(f"   首次等待：{self.config['wait_time_initial']}秒")
        
        # 首次等待 2 分钟
        time.sleep(self.config['wait_time_initial'])
        
        # 尝试获取结果
        result_text = self.analyze_article_async(title, paragraphs)
        
        if result_text:
            return self._parse_response(result_text, paragraphs)
        
        # 继续轮询，每分钟一次
        count = 1
        while count < max_count:
            print(f"   第{count+1}次等待：{self.config['wait_time_retry']}秒...")
            time.sleep(self.config['wait_time_retry'])
            
            result_text = self.analyze_article_async(title, paragraphs)
            
            if result_text:
                print(f"✅ 第{count+1}次尝试获取到结果")
                return self._parse_response(result_text, paragraphs)
            
            count += 1
        
        print(f"❌ 等待超时（{max_count}次），AI 仍未返回结果")
        return None
    
    def _parse_response(self, response_text: str, paragraphs: List[str]) -> Dict:
        """解析 AI 响应，直接保留完整Markdown内容"""
        try:
            # 直接使用原始响应作为解析内容
            analysis_content = response_text.strip()

            # 提取基础统计数据
            total_words = sum(len(p) for p in paragraphs)
            total_paras = len(paragraphs)

            # ==================== 构建段落数据（兼容旧逻辑） ====================
            paragraphs_data = []
            for i, para in enumerate(paragraphs):
                paragraphs_data.append({
                    'role': '分论点支撑',
                    'role_description': '',
                    'core_point': '',
                    'writing_techniques': [],
                    'word_count': len(para),
                    'learning_tips': '',
                    'original_text': para,
                })

            # ==================== 构建最终结果 ====================
            analysis_result = {
                'overall': {
                    'main_theme': '时政评论深度分析',
                    'writing_style': '人民时评风格',
                    'total_words': total_words,
                    'total_paras': total_paras,
                    # 完整的Markdown内容
                    'analysis_content': analysis_content,
                    # 兼容旧字段
                    'main_point': '',
                    'sub_points': [],
                    'stance_height': '',
                    'structure_type': '',
                    'structure_diagram': '',
                    'transition_technique': '',
                    'good_sentences': [],
                    'logic_analysis': '',
                    'writing_techniques': '',
                    'good_sentences_raw': '',
                    'analysis_report': '',
                    'stats': {
                        'total_paras': total_paras,
                        'total_words': total_words,
                        'main_points': 0,
                        'sub_points': 0,
                        'technique_counts': {},
                    }
                },
                'paragraphs': paragraphs_data,
                'structure': {
                    'argument_layers': 0,
                    'technique_summary': ''
                }
            }

            print(f"✅ 解析完成：完整Markdown内容已保留")

            return analysis_result

        except Exception as e:
            print(f"⚠️  解析失败：{e}")
            print(f"   原始响应：{response_text[:200]}...")
            import traceback
            traceback.print_exc()
            return None


# ==================== 段落分析器 ====================

class ParagraphAnalyzer:
    def __init__(self, ai_analyzer: Optional[BailianAsyncAnalyzer] = None):
        self.ai_analyzer = ai_analyzer
        self.ai_result = None
        self.ROLES = {
            '开头破题': {'description': '开门见山，直接点明主题', 'tips': '学习这种开门见山的破题方式'},
            '背景阐述': {'description': '阐述话题背景', 'tips': '学习由浅入深的展开方式'},
            '分论点': {'description': '围绕中心论点展开分析', 'tips': '学习观点 + 论据 + 分析的三层结构'},
            '过渡衔接': {'description': '承上启下', 'tips': '学习自然过渡的写法'},
            '举例论证': {'description': '通过案例支撑论点', 'tips': '学习用典型案例增强说服力'},
            '对比论证': {'description': '通过对比突出观点', 'tips': '学习选择对比对象和角度'},
            '引用论证': {'description': '引用名言或数据', 'tips': '学习恰当引用'},
            '结尾升华': {'description': '总结全文，升华主题', 'tips': '学习回扣开头的结尾写法'},
        }
    
    def analyze_with_ai(self, title: str, paragraphs: List[str]) -> bool:
        """使用 AI 异步分析文章"""
        if not self.ai_analyzer:
            return False
        
        # 提交任务并等待结果
        self.ai_result = self.ai_analyzer.wait_for_result(title, paragraphs)
        
        if self.ai_result:
            print(f"✅ AI 分析完成：{len(self.ai_result.get('paragraphs', []))}个段落")
            return True
        return False
    
    def analyze(self, para_text: str, para_index: int, total_paras: int, all_paragraphs: List[str]) -> Tuple[str, str, Dict]:
        """分析单个段落"""
        if not self.ai_result or 'paragraphs' not in self.ai_result:
            raise RuntimeError("必须先调用 analyze_with_ai()")
        
        ai_para = self.ai_result['paragraphs'][para_index] if para_index < len(self.ai_result['paragraphs']) else None
        if not ai_para:
            raise RuntimeError(f"缺少第{para_index+1}段的 AI 数据")
        
        role = ai_para.get('role', '分论点')
        return self._generate_analysis_from_ai(para_text, para_index, total_paras, role, ai_para, all_paragraphs)
    
    def _generate_analysis_from_ai(self, para_text: str, para_index: int, total_paras: int, role: str, ai_para: Dict, all_paragraphs: List[str]) -> Tuple[str, str, Dict]:
        """从 AI 结果生成 HTML"""
        role_info = self.ROLES.get(role, self.ROLES['分论点'])
        
        # 使用新的排版格式
        analysis_html = f"""
<div class="para-analysis">
    <div class="analysis-section">
        <h4>🎯 段落作用</h4>
        <p class="analysis-desc">{ai_para.get('role_description', role_info['description'])}</p>
    </div>
    
    <div class="analysis-section">
        <h4>💡 核心观点</h4>
        <p class="analysis-point">{ai_para.get('core_point', '')}</p>
    </div>
    
    <div class="analysis-section">
        <h4>✨ 写作手法</h4>
        <div class="technique-tags">
"""
        
        techniques = ai_para.get('writing_techniques', [])
        if techniques:
            for t in techniques:
                analysis_html += f'<span class="tech-tag">{t}</span>'
        else:
            analysis_html += '<span class="tech-tag">无特殊手法</span>'
        
        analysis_html += """
        </div>
    </div>
    
    <div class="analysis-section">
        <h4>📝 学习要点</h4>
        <p class="analysis-tips">{tips}</p>
    </div>
</div>
""".format(tips=ai_para.get('learning_tips', role_info['tips']))
        
        extra_info = {
            'word_count': ai_para.get('word_count', len(para_text)),
            'sentence_count': para_text.count('.') + para_text.count('!') + para_text.count('?'),
            'has_data': '数据支撑' in techniques,
            'has_quote': '引用论证' in techniques,
        }
        
        return role, analysis_html, extra_info

# ==================== 网页生成 ====================

def is_lead_paragraph(para: str) -> bool:
    """
    判断是否为导语段落
    规则：如果段落结尾没有句号（。！？），则视为导语
    """
    para = para.strip()
    if not para:
        return False
    # 检查结尾是否有中文句号、感叹号、问号
    last_char = para[-1]
    return last_char not in '。！？.'

def generate_web_page(title: str, paragraphs: List[str], original_url: str, publish_date: str, display_datetime: str, analyzer: ParagraphAnalyzer, ai_result: Dict):
    """生成网页"""
    
    print("\n🎨 正在生成网页...")
    display_date = publish_date.replace('-', '年', 1).replace('-', '月', 1) + '日'
    
    # 处理段落列表，判断是否有导语
    para_list = []
    has_lead = False
    lead_text = ''
    
    lead_paragraphs = []
    for para in paragraphs:
        if is_lead_paragraph(para):
            lead_paragraphs.append(para)
        else:
            break
    if lead_paragraphs:
        has_lead = True
        lead_text = '<br><br>'.join(lead_paragraphs)
        actual_paragraphs = paragraphs[len(lead_paragraphs):]
    else:
        actual_paragraphs = paragraphs
    
    # 构建正式段落列表（带序号）
    for i, para in enumerate(actual_paragraphs):
        para_list.append({
            'index': i + 1,
            'text': para,
        })
    
    # 从 AI 结果中提取数据
    overall = ai_result.get('overall', {})

    # 修正统计：段落数和字数不包含导语
    if has_lead:
        actual_para_count = len(para_list)
        actual_word_count = sum(len(p) for p in actual_paragraphs)
        overall['total_paras'] = actual_para_count
        overall['total_words'] = actual_word_count
        if 'stats' in overall:
            overall['stats']['total_paras'] = actual_para_count
            overall['stats']['total_words'] = actual_word_count

    # 加载模板
    env = Environment(loader=FileSystemLoader(BASE_CONFIG['templates_dir']), autoescape=True)
    template = env.get_template('daily_detail.html')
    
    # 渲染页面
    html = template.render(
        title=title,
        date=display_date,
        original_url=original_url,
        paragraphs=para_list,
        has_lead=has_lead,
        lead_text=lead_text,
        total_paras=len(para_list),
        overall=overall,
    )
    
    # 保存文件
    daily_dir = os.path.join(BASE_CONFIG['output_dir'], 'daily')
    os.makedirs(daily_dir, exist_ok=True)
    
    url_hash = hashlib.md5((title + publish_date).encode()).hexdigest()[:8]
    filename = f"{publish_date.replace('-', '')}_{url_hash}.html"
    output_path = os.path.join(daily_dir, filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ 详情页已生成：/daily/{filename}")
    
    # 更新列表
    update_article_list(title, display_datetime, original_url, filename, actual_paragraphs, ai_result)
    
    # 重新生成列表页
    regenerate_list_page(env)
    print(f"✅ 列表页已更新：/daily.html")

def clear_today_flags():
    """清除所有'今日更新'标记（每天运行时先执行）"""
    list_file = os.path.join(BASE_CONFIG['output_dir'], 'daily', 'list.json')
    if not os.path.exists(list_file):
        return
    
    try:
        with open(list_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        
        # 清除所有 is_today 标记
        for article in articles:
            article['is_today'] = False
        
        with open(list_file, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        
        print("✅ 已清除昨日的置顶标记")
    except Exception as e:
        print(f"⚠️  清除置顶标记失败：{e}")


def update_article_list(title: str, date: str, original_url: str, filename: str, paragraphs: List[str], ai_result: Dict):
    """更新文章列表 JSON"""
    list_file = os.path.join(BASE_CONFIG['output_dir'], 'daily', 'list.json')
    
    articles = []
    if os.path.exists(list_file) and os.path.getsize(list_file) > 0:
        try:
            with open(list_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)
        except:
            articles = []
    
    # 检查是否已存在
    for article in articles:
        if article.get('original_url') == original_url:
            print(f"⚠️  文章已在列表中")
            return
    
    # 检查日期格式是否已经包含"年月日"
    if '年' in date and '月' in date and '日' in date:
        display_date = date
    else:
        display_date = date.replace('-', '年', 1).replace('-', '月', 1) + '日'
    summary = paragraphs[0][:150] + '...' if paragraphs and len(paragraphs[0]) > 150 else (paragraphs[0] if paragraphs else '')
    
    # 从 AI 结果中提取信息
    overall = ai_result.get('overall', {})
    word_count = overall.get('total_words', sum(len(p) for p in paragraphs))
    
    # 新文章标记为今日更新
    new_article = {
        'date': display_date,
        'title': title,
        'url': f"/daily/{filename}",
        'original_url': original_url,
        'summary': summary,
        'word_count': word_count,
        'para_count': len(paragraphs),
        'is_today': True,  # 今日更新标记
    }
    
    # 插入到列表开头（置顶位置）
    articles.insert(0, new_article)
    
    with open(list_file, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f"✅ 文章列表已更新（共{len(articles)}篇），今日更新已置顶")

def regenerate_list_page(env: Environment):
    """重新生成列表页"""
    list_file = os.path.join(BASE_CONFIG['output_dir'], 'daily', 'list.json')
    articles = []
    if os.path.exists(list_file):
        try:
            with open(list_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)
        except:
            pass
    
    if not articles:
        return
    
    # 排序函数
    def parse_date(article):
        date_str = article.get('date', '')
        # 格式：2026年02月12日 -> 20260212
        match = re.match(r'(\d{4})年(\d{2})月(\d{2})日', date_str)
        if match:
            return f"{match.group(1)}{match.group(2)}{match.group(3)}"
        return '00000000'
    
    # 分离置顶和非置顶文章
    today_articles = [a for a in articles if a.get('is_today')]
    other_articles = [a for a in articles if not a.get('is_today')]
    
    # 非置顶文章按日期降序
    other_articles.sort(key=parse_date, reverse=True)
    
    # 合并：置顶在前
    sorted_articles = today_articles + other_articles
    
    list_template = env.get_template('daily.html')
    list_html = list_template.render(
        articles=sorted_articles,
        update_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    )
    
    with open(os.path.join(BASE_CONFIG['output_dir'], 'daily.html'), 'w', encoding='utf-8') as f:
        f.write(list_html)

# ==================== 主函数 ====================

def main():
    print("=" * 70)
    print(f"🕒 开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 清除昨日的置顶标记（每天运行时先清除）
    print("\n🔄 步骤 0: 清除昨日的置顶标记...")
    clear_today_flags()
    
    # 创建分析器
    ai_analyzer = BailianAsyncAnalyzer()
    analyzer = ParagraphAnalyzer(ai_analyzer)
    
    # 获取文章
    print("\n📋 步骤 1: 获取最新未处理的文章...")
    article = get_latest_unprocessed_article()
    
    if not article:
        print("\n❌ 没有找到合适的未处理文章")
        sys.exit(0)
    
    title = article['title']
    url = article['url']
    publish_time = article['publish_time']
    
    # 格式化日期和时间
    if isinstance(publish_time, datetime):
        publish_date = publish_time.strftime('%Y-%m-%d')
        publish_datetime = publish_time.strftime('%Y-%m-%d %H:%M')
    else:
        date_str = str(publish_time) if publish_time else ''
        
        # 处理带时分的时间格式：2026年03月30日 08:56 或 2026-03-30 08:56
        if date_str and '年' in date_str:
            match = re.match(r'(\d{4})年(\d{2})月(\d{2})日\s*(\d{2}:\d{2})?', date_str)
            if match:
                year, month, day, time_part = match.groups()
                publish_date = f"{year}-{month}-{day}"
                publish_datetime = f"{year}-{month}-{day} {time_part}" if time_part else publish_date
            else:
                publish_date = date_str[:10] if len(date_str) >= 10 else ''
                publish_datetime = date_str
        elif date_str and '-' in date_str and len(date_str) >= 10:
            publish_date = date_str[:10]
            publish_datetime = date_str[:16] if len(date_str) >= 16 else date_str[:10]
        else:
            # 从 URL 中提取日期作为备选
            # URL 格式：http://opinion.people.com.cn/n1/2025/0429/c1003-40470344.html
            url_match = re.search(r'/n1/(\d{4})/(\d{4})/', url)
            if url_match:
                year = url_match.group(1)
                month_day = url_match.group(2)
                publish_date = f"{year}-{month_day[:2]}-{month_day[2:]}"
                publish_datetime = publish_date
            else:
                # 最后使用当天日期
                publish_date = datetime.now().strftime('%Y-%m-%d')
                publish_datetime = publish_date
    
    if not publish_date:
        publish_date = datetime.now().strftime('%Y-%m-%d')
        publish_datetime = publish_date
    
    display_date = publish_date.replace('-', '年', 1).replace('-', '月', 1) + '日'
    display_datetime = publish_datetime.replace('-', '年', 1).replace('-', '月', 1).replace(' ', '日 ', 1) if len(publish_datetime) > 10 else display_date
    print(f"   标题：{title}")
    print(f"   链接：{url}")
    print(f"   时间：{display_datetime}")
    
    # 获取并清理内容
    print(f"\n📖 步骤 2: 获取并清理文章内容...")
    paragraphs, url = get_and_clean_article(url)
    
    if not paragraphs:
        print("\n❌ 获取文章内容失败")
        sys.exit(1)
    
    # AI 异步分析
    print(f"\n🤖 步骤 3: 提交 AI 分析并等待结果...")
    if not analyzer.analyze_with_ai(title, paragraphs):
        print("❌ AI 分析失败")
        sys.exit(1)
    
    # 生成网页
    print(f"\n🎨 步骤 4: 生成网页...")
    generate_web_page(title, paragraphs, url, publish_date, display_datetime, analyzer, analyzer.ai_result)
    
    print("\n" + "=" * 70)
    print(f"✅ 完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print(f"\n🌐 访问地址：https://binjian.cloud/daily.html")

if __name__ == '__main__':
    main()
