import json, re

# Смотрим реальную структуру "before" Stage3 файла
f = json.load(open('/opt/glava/exports/karakulina_book_FINAL_stage3_20260412_132158.json'))
print("Top-level keys:", list(f.keys()))

# Ищем все возможные места с текстом
def count_content(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            count_content(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            count_content(v, f"{path}[{i}]")
    elif isinstance(obj, str) and len(obj) > 200:
        print(f"  {path}: {len(obj)} симв")

count_content(f)
