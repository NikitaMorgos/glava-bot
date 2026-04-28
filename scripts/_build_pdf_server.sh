#!/bin/bash
set -e
cd /opt/glava

echo "=== Скачиваем шрифты ==="
mkdir -p fonts

# Playfair Display
wget -q "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf" -O fonts/PlayfairDisplay-Regular.ttf || \
  wget -q "https://fonts.gstatic.com/s/playfairdisplay/v30/nuFiD-vYSZviVYUb_rj3ij__anPXBYf9b0.ttf" -O fonts/PlayfairDisplay-Regular.ttf

# Если variable font - копируем как Bold и Italic тоже
cp fonts/PlayfairDisplay-Regular.ttf fonts/PlayfairDisplay-Bold.ttf
cp fonts/PlayfairDisplay-Regular.ttf fonts/PlayfairDisplay-Italic.ttf

# Merriweather
wget -q "https://github.com/google/fonts/raw/main/ofl/merriweather/Merriweather-Regular.ttf" -O fonts/Merriweather-Regular.ttf
cp fonts/Merriweather-Regular.ttf fonts/Merriweather-Bold.ttf
cp fonts/Merriweather-Regular.ttf fonts/Merriweather-Italic.ttf

# Raleway
wget -q "https://github.com/google/fonts/raw/main/ofl/raleway/static/Raleway-Regular.ttf" -O fonts/Raleway-Regular.ttf
wget -q "https://github.com/google/fonts/raw/main/ofl/raleway/static/Raleway-Light.ttf" -O fonts/Raleway-Light.ttf
wget -q "https://github.com/google/fonts/raw/main/ofl/raleway/static/Raleway-Bold.ttf" -O fonts/Raleway-Bold.ttf

echo "Шрифты: $(ls fonts/*.ttf | wc -l) файлов"

echo ""
echo "=== Создаём симлинки для фото ==="
python3 - <<'PYEOF'
import json, os
from pathlib import Path

manifest = json.load(open('exports/karakulina_photos/manifest.json', encoding='utf-8'))
photos_dir = Path('exports/karakulina_photos')

for e in manifest:
    if e.get('exclude'):
        continue
    idx = e['index']
    photo_id = f"photo_{idx:03d}"
    src = photos_dir / e['filename']
    dst = photos_dir / f"{photo_id}.jpg"
    if src.exists() and not dst.exists():
        os.symlink(src.resolve(), dst)
        print(f"  {photo_id}.jpg -> {e['filename']}")
    elif dst.exists():
        print(f"  {photo_id}.jpg уже есть")

print(f"Симлинки созданы")
PYEOF

echo ""
echo "=== Запускаем сборку PDF ==="
cd /opt/glava
.venv/bin/python exports/karakulina_iter3_layout_code_20260330_105105.py
echo "DONE"
