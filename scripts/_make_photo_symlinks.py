import json, os
from pathlib import Path

os.chdir('/opt/glava')
manifest = json.load(open('exports/karakulina_photos/manifest.json', encoding='utf-8'))
photos_dir = Path('exports/karakulina_photos')

for e in manifest:
    if e.get('exclude'):
        continue
    idx = e['index']
    src = photos_dir / e['filename']
    dst = photos_dir / f"photo_{idx:03d}.jpg"
    if src.exists() and not dst.exists():
        os.symlink(src.resolve(), dst)
        print(f"  {dst.name} -> {e['filename']}")
    elif dst.exists():
        print(f"  {dst.name} OK")

print("Готово")
