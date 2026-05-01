import json
layout = json.load(open('/opt/glava/exports/karakulina_stage4_layout_iter1_20260501_075223.json'))
book = json.load(open('/opt/glava/checkpoints/karakulina/proofreader.json'))
if 'content' in book:
    book = book['content']

pages = layout.get('pages', [])
for page in pages:
    for el in page.get('elements', []):
        etype = el.get('type', '')
        if etype in ('subheading', 'section_header'):
            ch_id = el.get('chapter_id', '')
            ref = el.get('subheading_ref') or el.get('paragraph_ref') or el.get('paragraph_id', '')
            print(f'subheading: page {page["page_number"]} ch={ch_id} ref={ref} type={etype}')

# Also check book paragraphs of type subheading
from pipeline_utils import prepare_book_for_layout
import sys, os
sys.path.insert(0, '/opt/glava')
prepared = prepare_book_for_layout(book)
for ch in prepared.get('chapters', []):
    for p in ch.get('paragraphs', []):
        if p.get('type') == 'subheading':
            print(f'book subheading: {ch["id"]}/{p["id"]}: {p["text"][:60]}')
print('done')
