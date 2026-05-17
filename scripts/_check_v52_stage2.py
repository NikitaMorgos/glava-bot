import json, glob, sys, os
os.chdir('/opt/glava')

# Check revision volume
files = sorted(glob.glob('exports/stage2_v52/karakulina_revision_volume_iter1_*.json'))
if not files:
    print('revision_volume: NOT FOUND')
else:
    with open(files[-1], encoding='utf-8') as f:
        d = json.load(f)
    print('=== REVISION VOLUME ===')
    print('verdict:', d.get('verdict'))
    print('chars_before:', d.get('chars_before'))
    print('chars_after:', d.get('chars_after'))
    print('drop_ratio:', d.get('drop_ratio'))
    print('legitimate_count:', d.get('legitimate_deletion_count'))
    cdet = d.get('chapter_details', {})
    for ch, v in cdet.items():
        print('  ', ch, 'before=', v.get('chars_before'), 'after=', v.get('chars_after'))

# Check FC iter1 errors summary
fc_files = sorted(glob.glob('exports/stage2_v52/karakulina_fc_report_iter1_*.json'))
if not fc_files:
    print('FC iter1: NOT FOUND')
else:
    with open(fc_files[-1], encoding='utf-8') as f:
        fc = json.load(f)
    errors = fc.get('errors', [])
    print('\n=== FC ITER1 ERRORS ===')
    print('total errors:', len(errors))
    print('verdict:', fc.get('verdict'))
    for i, e in enumerate(errors):
        print(f'  [{i+1}] ch={e.get("chapter_id")} type={e.get("type")} sev={e.get("severity")} ld={e.get("legitimate_deletion")}')
        fix = e.get("fix_instruction", "")
        print(f'       fix: {fix[:120]}')
