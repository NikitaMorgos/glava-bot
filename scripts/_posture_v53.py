import json, glob, sys, os
os.chdir('/opt/glava')

# 1. Cucumbers in book_FINAL_stage3
print('=== ОГУРЦЫ / МОЛДАВИЯ / ЧЕМОДАН ===')
s3_files = sorted(glob.glob('exports/stage3_v53/karakulina_v53_book_FINAL_stage3_*.json'))
if s3_files:
    with open(s3_files[-1], encoding='utf-8') as f:
        book = json.load(f)
    for ch in book.get('chapters', []):
        ch_id = ch.get('id', '')
        text = ' '.join(p.get('text','') for p in ch.get('paragraphs', []) if p.get('text'))
        hits = [w for w in ['огурц','молдави','чемодан'] if w.lower() in text.lower()]
        if hits:
            print(f'  {ch_id}: {hits}')
            # Show snippet
            for p in ch.get('paragraphs', []):
                t = p.get('text', '')
                if any(w.lower() in t.lower() for w in ['огурц','молдави','чемодан']):
                    print(f'    SNIPPET: {t[:200]}')
else:
    print('  book_FINAL_stage3 not found')

# 2. Documents duplication check
print('\n=== ДОКУМЕНТЫ (паспорт/свидетельство) ===')
doc_words = ['паспорт','свидетельств','метрик']
if s3_files:
    for ch in book.get('chapters', []):
        ch_id = ch.get('id', '')
        text = ' '.join(p.get('text','') for p in ch.get('paragraphs', []) if p.get('text'))
        hits = [w for w in doc_words if w.lower() in text.lower()]
        if hits:
            print(f'  {ch_id}: {hits}')

# 3. Regression #5 - Tatyana in bio_data.family
print('\n=== РЕГРЕССИЯ #5 — ТАТЬЯНА В bio_data.family ===')
if s3_files:
    bio = book.get('bio_data', {})
    family = bio.get('family', [])
    tatyana_found = any('татьян' in str(m).lower() for m in family)
    print(f'  family members: {len(family)}')
    print(f'  Татьяна найдена: {tatyana_found}')
    for m in family:
        name = m.get('name','') if isinstance(m, dict) else str(m)
        if 'татьян' in name.lower():
            print(f'    → {m}')

# 4. Regression #6 - medal in bio_data.awards
print('\n=== РЕГРЕССИЯ #6 — МЕДАЛЬ В bio_data.awards ===')
if s3_files:
    awards = bio.get('awards', [])
    print(f'  awards count: {len(awards)}')
    for a in awards:
        label = a.get('label','') if isinstance(a, dict) else str(a)
        year = a.get('year','') if isinstance(a, dict) else ''
        print(f'  → {label} ({year})')

# 5. scope_merge artifacts
print('\n=== SCOPE MERGE ARTIFACTS ===')
sm_files = sorted(glob.glob('exports/stage2_v53/karakulina_scope_merge_iter*.json'))
print(f'  scope_merge files found: {len(sm_files)}')
for smf in sm_files:
    with open(smf, encoding='utf-8') as f:
        sm = json.load(f)
    restored = sm.get('chapters_restored', [])
    print(f'  {os.path.basename(smf)}: chapters_restored={restored}')

# 6. FC iter count and legitimate_deletion flags
print('\n=== FC ITERATIONS ===')
fc_files = sorted(glob.glob('exports/stage2_v53/karakulina_fc_report_iter*.json'))
print(f'  FC iterations: {len(fc_files)}')
for fcf in fc_files:
    with open(fcf, encoding='utf-8') as f:
        fc = json.load(f)
    ld_count = sum(1 for e in fc.get('errors',[]) if e.get('legitimate_deletion'))
    print(f'  {os.path.basename(fcf)}: verdict={fc.get("verdict")} errors={len(fc.get("errors",[]))} ld={ld_count}')

# 7. Volume stats
print('\n=== ОБЪЁМ (Stage 2 revision volume) ===')
rv_files = sorted(glob.glob('exports/stage2_v53/karakulina_revision_volume_iter*.json'))
for rvf in rv_files:
    with open(rvf, encoding='utf-8') as f:
        rv = json.load(f)
    print(f'  {os.path.basename(rvf)}: verdict={rv.get("verdict")} before={rv.get("chars_before")} after={rv.get("chars_after")}')
