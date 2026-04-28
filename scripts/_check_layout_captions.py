import json

with open('exports/karakulina_layout_20260404.json', encoding='utf-8') as f:
    layout = json.load(f)

sg = layout.get('style_guide', {})
print("=== style_guide ===")
print(json.dumps(sg, ensure_ascii=False, indent=2))
