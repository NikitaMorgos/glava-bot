import re
from pathlib import Path

txt = Path('exports/karakulina_FINAL_stage3_20260329_065332.txt').read_text(encoding='utf-8')

chapter_blocks = re.split(r'={20,}\n(ch_\d+) \| (.+?)\n={20,}', txt)

chapters = []
for i in range(1, len(chapter_blocks), 3):
    ch_id    = chapter_blocks[i]
    ch_title = chapter_blocks[i+1]
    ch_content = chapter_blocks[i+2].strip()
    sections = re.split(r'\n## (.+)\n', ch_content)
    sec_list = []
    if sections[0].strip():
        sec_list.append({'title': None, 'text': sections[0].strip()})
    for j in range(1, len(sections), 2):
        sec_list.append({'title': sections[j], 'text': sections[j+1].strip()})
    chapters.append({'id': ch_id, 'title': ch_title, 'sections': sec_list})

for ch in chapters:
    print(ch['id'], '|', ch['title'], '—', len(ch['sections']), 'секций')
    for s in ch['sections']:
        paras = [p for p in s['text'].split('\n\n') if p.strip()]
        t = '  [' + (s['title'] or 'без заголовка') + ']'
        print(t, ':', len(paras), 'абз.')
