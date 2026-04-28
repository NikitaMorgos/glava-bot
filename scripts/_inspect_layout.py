import json
d = json.load(open('exports/karakulina_stage4_layout_iter1_20260402_112132.json', encoding='utf-8'))
pages = d['pages']

cover = next(p for p in pages if p['type'] == 'cover')
print('COVER elements:')
for e in cover.get('elements', []):
    print(' ', json.dumps(e, ensure_ascii=False)[:300])

print()
for p in pages:
    if p['type'] == 'text_with_photo':
        print('TEXT_WITH_PHOTO page', p['page_number'])
        for e in p.get('elements', []):
            if e['type'] == 'paragraph':
                print(f'  paragraph: {len(e["text"])} chars')
            else:
                print(f'  {e["type"]}: layout={e.get("layout")} photo_id={e.get("photo_id")} caption={e.get("caption", "")}')
        break

print()
# Check fonts on server side via registered fonts
import reportlab
from reportlab.pdfbase import pdfmetrics
print('ReportLab version:', reportlab.Version)
from pathlib import Path
freefont_paths = [
    '/usr/share/fonts/truetype/freefont/FreeSerif.ttf',
    '/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf',
    '/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf',
    '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
    '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
]
print('Font paths exist locally:')
for p in freefont_paths:
    print(f'  {Path(p).name}: {Path(p).exists()}')
