#!/usr/bin/env python3
"""Downloads Google Fonts TTF files from GitHub to /opt/glava/fonts/"""
import urllib.request
import pathlib

FONTS_DIR = pathlib.Path("/opt/glava/fonts")
FONTS_DIR.mkdir(parents=True, exist_ok=True)

BASE = "https://github.com/google/fonts/raw/main"

FONT_FILES = {
    # Playfair Display
    "PlayfairDisplay-Regular.ttf":     f"{BASE}/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
    "PlayfairDisplay-Bold.ttf":        f"{BASE}/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
    "PlayfairDisplay-Italic.ttf":      f"{BASE}/ofl/playfairdisplay/PlayfairDisplay-Italic%5Bwght%5D.ttf",
    # Merriweather
    "Merriweather-Regular.ttf":        f"{BASE}/ofl/merriweather/Merriweather-Regular.ttf",
    "Merriweather-Bold.ttf":           f"{BASE}/ofl/merriweather/Merriweather-Bold.ttf",
    "Merriweather-Italic.ttf":         f"{BASE}/ofl/merriweather/Merriweather-Italic.ttf",
    # Raleway
    "Raleway-Regular.ttf":             f"{BASE}/ofl/raleway/Raleway%5Bwght%5D.ttf",
    "Raleway-Light.ttf":               f"{BASE}/ofl/raleway/Raleway%5Bwght%5D.ttf",
}

for filename, url in FONT_FILES.items():
    target = FONTS_DIR / filename
    if target.exists():
        print(f"[SKIP] {filename}")
        continue
    print(f"[DOWNLOAD] {filename} ...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        target.write_bytes(data)
        print(f"  → {len(data)} bytes OK")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")

ttf_files = list(FONTS_DIR.glob("*.ttf"))
print(f"\n[DONE] {len(ttf_files)} TTF files in {FONTS_DIR}:")
for f in sorted(ttf_files):
    print(f"  {f.name} ({f.stat().st_size} bytes)")
