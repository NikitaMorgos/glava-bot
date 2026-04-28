import json, sys, pathlib
sys.stdout.reconfigure(encoding='utf-8')
d = json.load(open('exports/karakulina_layout_20260404.json', encoding='utf-8'))

# Callouts and historical notes across all pages
print("=== CALLOUTS / HISTORICAL NOTES ===")
for p in d['pages']:
    pn = p['page_number']
    for e in p.get('elements', []):
        t = e.get('type','')
        if t in ('callout','historical_note','historical','hist_note'):
            print(f"  p{pn:02d} [{t}]: text={e.get('text','')[:80]!r}")
            print(f"         color={e.get('color','—')} bg={e.get('background','—')} border={e.get('border_color','—')}")

# Page 7 photo
print()
print("=== PAGE 7 ===")
for e in d['pages'][6].get('elements',[]):
    print(' ', e)

# Check photo_017 dimensions
print()
photos_dir = pathlib.Path('exports/karakulina_photos')
from PIL import Image as PILImage
for p in d['pages']:
    for e in p.get('elements',[]):
        if e.get('type') == 'photo' and e.get('layout','') in ('wrap_right','wrap_left'):
            pid = e.get('photo_id','')
            manifest = json.load(open(photos_dir / 'manifest.json', encoding='utf-8'))
            for m in manifest:
                idx = m['index']
                key = f'photo_{idx:03d}'
                if key == pid:
                    path = photos_dir / m['filename']
                    if path.exists():
                        with PILImage.open(path) as img:
                            w, h = img.size
                        orientation = 'VERTICAL' if h > w else 'HORIZONTAL'
                        print(f"  p{p['page_number']:02d} {pid} layout={e['layout']} -> {m['filename']} {w}x{h} [{orientation}]")

# Cover elements
print()
print("=== COVER YEARS ===")
for e in d['pages'][0].get('elements',[]):
    if e.get('type') in ('cover_years','cover_description','cover_title','cover_subtitle'):
        print(' ', e.get('type'), '->', e.get('text',''))
