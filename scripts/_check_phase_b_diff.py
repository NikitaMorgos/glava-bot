import json, sys, re

# 1. Проверяем fact_map на наличие пианино/шубы
fm = json.load(open('/opt/glava/checkpoints/karakulina/fact_map.json'))
print("=== FACT_MAP: поиск пианино/шуба ===")
fm_str = json.dumps(fm, ensure_ascii=False)
for word in ['пианино', 'шуб', 'piano']:
    hits = [m.start() for m in re.finditer(word, fm_str, re.IGNORECASE)]
    if hits:
        for h in hits:
            print(f"  [{word}] @ {h}: ...{fm_str[max(0,h-60):h+80]}...")
    else:
        print(f"  [{word}] — НЕТ В FACT_MAP")

# 2. Проверяем оригинальный транскрипт (48KB meeting)
print("\n=== MEETING TRANSCRIPT: поиск пианино/шуба ===")
tr = open('/opt/glava/exports/karakulina_meeting_transcript_20260403.txt', encoding='utf-8').read()
for word in ['пианино', 'шуб']:
    hits = [m.start() for m in re.finditer(word, tr, re.IGNORECASE)]
    if hits:
        for h in hits:
            print(f"  [{word}] @ {h}: ...{tr[max(0,h-80):h+100].replace(chr(10),' ')}...")
    else:
        print(f"  [{word}] — НЕТ В ТРАНСКРИПТЕ")

# 3. Сравниваем объёмы глав до Phase B и после
print("\n=== ОБЪЁМ ГЛАВ: ДО Phase B (stage3 20260412_132158) ===")
s3_before = json.load(open('/opt/glava/exports/karakulina_book_FINAL_stage3_20260412_132158.json'))
book_before = s3_before.get('book_final') or s3_before
for ch in book_before.get('chapters', []):
    content = ch.get('content') or ''
    print(f"  {ch['id']}: {len(content)} симв")

print("\n=== ОБЪЁМ ГЛАВ: ПОСЛЕ Phase B (stage3 20260412_144718) ===")
s3_after = json.load(open('/opt/glava/exports/karakulina_pb_book_FINAL_stage3_20260412_144718.json'))
book_after = s3_after.get('book_final') or s3_after
for ch in book_after.get('chapters', []):
    content = ch.get('content') or ''
    print(f"  {ch['id']}: {len(content)} симв")
