import json, glob, os
os.chdir('/opt/glava')

# Check fact_map for cucumber
print('=== ОГУРЦЫ В FACT_MAP v53b ===')
fm_files = sorted(glob.glob('exports/karakulina_v53b/karakulina_fact_map_full_*.json'))
if fm_files:
    with open(fm_files[-1], encoding='utf-8') as f:
        fm = json.load(f)
    print(f'  timeline events: {len(fm.get("timeline", []))}')
    found = False
    for ev in fm.get('timeline', []):
        desc = str(ev.get('description', '')) + ' ' + str(ev.get('source_quote', ''))
        if any(w in desc.lower() for w in ['огурц', 'молдави', 'чемодан']):
            print(f'  FOUND: {ev.get("id")} | {desc[:250]}')
            found = True
    if not found:
        print('  НЕ найдено в timeline')
else:
    print('  fact_map_full NOT FOUND')

# Check draft v1 for cucumber (before FC/GW revision)
print('\n=== ОГУРЦЫ В ЧЕРНОВИКЕ v1 (до FC) ===')
draft_files = sorted(glob.glob('exports/stage2_v53b/karakulina_book_draft_v1_*.json'))
if draft_files:
    with open(draft_files[-1], encoding='utf-8') as f:
        d = json.load(f)
    found_in_draft = False
    for ch in d.get('chapters', []):
        ch_id = ch.get('id', '')
        text = ' '.join(p.get('text', '') for p in ch.get('paragraphs', []) if p.get('text'))
        hits = [w for w in ['огурц', 'молдави', 'чемодан'] if w.lower() in text.lower()]
        if hits:
            print(f'  {ch_id}: {hits}')
            found_in_draft = True
    if not found_in_draft:
        print('  НЕ найдено в черновике v1')
else:
    print('  draft v1 NOT FOUND')

# Transcript direct check
print('\n=== ОГУРЦЫ В TR2 (cleaned transcript) ===')
tr_files = sorted(glob.glob('exports/karakulina_v53b/karakulina_combined_cleaned_*.txt'))
if tr_files:
    with open(tr_files[-1], encoding='utf-8') as f:
        tr = f.read()
    for w in ['огурц', 'молдави', 'чемодан']:
        count = tr.lower().count(w)
        if count > 0:
            # Find context
            idx = tr.lower().find(w)
            print(f'  "{w}": {count} раз. Пример: ...{tr[max(0,idx-50):idx+100]}...')

# Chapter structure of book_FINAL
print('\n=== СТРУКТУРА book_FINAL_stage3_v53b ===')
s3_files = sorted(glob.glob('exports/stage3_v53b/karakulina_v53b_book_FINAL_stage3_*.json'))
if s3_files:
    with open(s3_files[-1], encoding='utf-8') as f:
        book = json.load(f)
    for ch in book.get('chapters', []):
        ch_id = ch.get('id', '')
        paras = ch.get('paragraphs', [])
        text = ' '.join(p.get('text', '') for p in paras if p.get('text'))
        print(f'  {ch_id}: {len(text)} симв, {len(paras)} абз')
        if text:
            print(f'    first 100: {text[:100]}')
