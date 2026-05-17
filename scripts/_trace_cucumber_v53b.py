import json, glob, os
os.chdir('/opt/glava')

words = ['огурц', 'молдави', 'чемодан']

def check_book(path, label):
    with open(path, encoding='utf-8') as f:
        book = json.load(f)
    found = []
    for ch in book.get('chapters', []):
        ch_id = ch.get('id', '')
        text = ' '.join(p.get('text', '') for p in ch.get('paragraphs', []) if p.get('text'))
        hits = [w for w in words if w.lower() in text.lower()]
        if hits:
            found.append(ch_id)
            for p in ch.get('paragraphs', []):
                t = p.get('text', '')
                if any(w.lower() in t.lower() for w in words):
                    print(f'  {label} / {ch_id}: {t[:200]}')
    return found

# Stage 2 drafts
print('=== СЛЕД ОГУРЦОВ ПО ВЕРСИЯМ ===')
for pat, label in [
    ('exports/stage2_v53b/karakulina_book_draft_v1_*.json', 'draft_v1'),
    ('exports/stage2_v53b/karakulina_book_draft_v2_*.json', 'draft_v2 (after historian)'),
    ('exports/stage2_v53b/karakulina_book_draft_v3_*.json', 'draft_v3 (after GW revision 1)'),
    ('exports/stage2_v53b/karakulina_book_draft_v3_merged_*.json', 'draft_v3_merged'),
    ('exports/stage2_v53b/karakulina_book_FINAL_*.json', 'book_FINAL_stage2'),
    ('exports/stage3_v53b/karakulina_v53b_book_stage3_liteditor_*.json', 'after_liteditor'),
    ('exports/stage3_v53b/karakulina_v53b_book_FINAL_stage3_*.json', 'book_FINAL_stage3'),
]:
    files = sorted(glob.glob(pat))
    if not files:
        print(f'  {label}: FILE NOT FOUND')
        continue
    try:
        found = check_book(files[-1], label)
        if not found:
            print(f'  {label}: НЕ НАЙДЕНО (cucumbers gone here)')
    except Exception as e:
        print(f'  {label}: ERROR {e}')
