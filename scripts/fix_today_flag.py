"""修正置顶标记：清除全部 is_today，只给 9/4 那篇置顶，再重新渲染 daily.html"""
import json, sys
sys.path.insert(0, '/home/ubuntu')
import daily_people_article_push_v3 as m
from jinja2 import Environment, FileSystemLoader

LIST = '/var/www/binjian.cloud/daily/list.json'
# 2026-09-04 发布的《"到中国出差"的新变化（人民时评）》
TODAY_URL = 'http://opinion.people.com.cn/n1/2026/0904/c461529-40792109.html'

arts = json.load(open(LIST, encoding='utf-8'))

for a in arts:
    a['is_today'] = False

hit = [a for a in arts if a.get('original_url') == TODAY_URL]
if len(hit) != 1:
    print('❌ 匹配到 %d 条，预期 1 条，中止' % len(hit))
    sys.exit(1)

hit[0]['is_today'] = True
print('置顶改为：%s  %s' % (hit[0].get('date'), hit[0].get('title')))

with open(LIST, 'w', encoding='utf-8') as f:
    json.dump(arts, f, ensure_ascii=False, indent=2)

env = Environment(loader=FileSystemLoader(m.BASE_CONFIG['templates_dir']))
m.regenerate_list_page(env)
print('✅ daily.html 已重新生成')
