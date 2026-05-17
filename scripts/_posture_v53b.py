import json, glob, os
os.chdir('/opt/glava')

# 1. Cucumbers in book_FINAL_stage3_v53b
print('=== ОГУРЦЫ / МОЛДАВИЯ / ЧЕМОДАН ===')
s3_files = sorted(glob.glob('exports/stage3_v53b/karakulina_v53b_book_FINAL_stage3_*.json'))
if s3_files:
    with open(s3_files[-1], encoding='utf-8') as f:
        book = json.load(f)
    found_any = False
    for ch in book.get('chapters', []):
        ch_id = ch.get('id', '')
        paras = ch.get('paragraphs', [])
        for p in paras:
            t = p.get('text', '')
            if any(w.lower() in t.lower() for w in ['огурц', 'молдави', 'чемодан']):
                print(f'  {ch_id}: FOUND')
                print(f'    SNIPPET: {t[:250]}')
                found_any = True
    if not found_any:
        print('  НЕ найдено ни в одной главе')
else:
    print('  book_FINAL_stage3_v53b not found')

# 2. Documents check
print('\n=== ДОКУМЕНТЫ (паспорт/свидетельство) ===')
doc_words = ['паспорт', 'свидетельств', 'метрик', 'рождени']
doc_chapters = {}
if s3_files:
    for ch in book.get('chapters', []):
        ch_id = ch.get('id', '')
        text = ' '.join(p.get('text', '') for p in ch.get('paragraphs', []) if p.get('text'))
        hits = [w for w in doc_words if w.lower() in text.lower()]
        if hits:
            doc_chapters[ch_id] = hits
            print(f'  {ch_id}: {hits}')
    if not doc_chapters:
        print('  Документы не найдены ни в одной главе')
    else:
        ch_ids = list(doc_chapters.keys())
        if len(ch_ids) == 1:
            print(f'  Регрессия #4: ✅ документы только в {ch_ids[0]}')
        else:
            print(f'  Регрессия #4: ⚠️  документы в нескольких главах: {ch_ids}')

# 3. scope_merge artifacts
print('\n=== SCOPE MERGE ARTIFACTS ===')
sm_files = sorted(glob.glob('exports/stage2_v53b/karakulina_scope_merge_iter*.json'))
print(f'  scope_merge files found: {len(sm_files)}')
for smf in sm_files:
    with open(smf, encoding='utf-8') as f:
        sm = json.load(f)
    restored = sm.get('chapters_restored', [])
    print(f'  {os.path.basename(smf)}: chapters_restored={restored}')
    if restored:
        for ch in restored:
            print(f'    → restored: {ch}')

# 4. FC iterations
print('\n=== FC ITERATIONS ===')
fc_files = sorted(glob.glob('exports/stage2_v53b/karakulina_fc_report_iter*.json'))
print(f'  FC iterations: {len(fc_files)}')
for fcf in fc_files:
    with open(fcf, encoding='utf-8') as f:
        fc = json.load(f)
    ld_count = sum(1 for e in fc.get('errors', []) if e.get('legitimate_deletion'))
    print(f'  {os.path.basename(fcf)}: verdict={fc.get("verdict")} errors={len(fc.get("errors", []))} ld={ld_count}')

# 5. revision volume
print('\n=== REVISION VOLUME ===')
rv_files = sorted(glob.glob('exports/stage2_v53b/karakulina_revision_volume_iter*.json'))
for rvf in rv_files:
    with open(rvf, encoding='utf-8') as f:
        rv = json.load(f)
    print(f'  {os.path.basename(rvf)}: verdict={rv.get("verdict")} before={rv.get("chars_before")} after={rv.get("chars_after")}')

# 6. Regressions #5/#6
print('\n=== РЕГРЕССИИ #5/#6 ===')
if s3_files:
    bio = book.get('bio_data', {})
    family = bio.get('family', [])
    awards = bio.get('awards', [])
    tatyana = any('татьян' in str(m).lower() for m in family)
    print(f'  #5 Татьяна в family: {tatyana} (family={len(family)} entries)')
    print(f'  #6 awards: {len(awards)} записей')
    for a in awards:
        print(f'    → {a.get("label", "")} ({a.get("year", "")})')

# 7. Fidelity check details
print('\n=== FIDELITY DETAILS (из лога) ===')
print('  hist_03 mismatch: ch_02/hist_03 в book, ch_04/hist_03 в layout (позиционная ошибка LD)')
print('  Тип: COMPLETENESS warning, не ERROR. Pipeline завершился.')

# 8. Book structure
print('\n=== СТРУКТУРА КНИГИ v53b ===')
if s3_files:
    for ch in book.get('chapters', []):
        ch_id = ch.get('id', '')
        paras = ch.get('paragraphs', [])
        text = ' '.join(p.get('text', '') for p in paras if p.get('text'))
        callouts = len(ch.get('callouts', []))
        hist = len(ch.get('historical_notes', []))
        print(f'  {ch_id}: {len(text)} симв, {len(paras)} абз, {callouts} callout, {hist} hist_note')
