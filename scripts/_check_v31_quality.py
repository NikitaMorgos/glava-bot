import json, re, glob, sys
sys.path.insert(0, '/opt/glava')
from checkpoint_utils import save_checkpoint

RUN = '/opt/glava/collab/runs/karakulina_v31_20260421_042318'
EXPORTS = '/opt/glava/exports/karakulina_v31_run_20260421_042318'

# Load Phase B book
pb = json.load(open(f'{RUN}/book_FINAL_phase_b_v31.json'))
book = pb.get('book_final') or pb
chs = book.get('chapters', [])
ch01 = next((c for c in chs if (c.get('id') or c.get('chapter_id')) == 'ch_01'), {})
ch02 = next((c for c in chs if (c.get('id') or c.get('chapter_id')) == 'ch_02'), {})

bio = ch01.get('bio_data') or {}
tl = ch01.get('timeline') or bio.get('timeline') or []
hn = pb.get('historical_notes', [])

print("=== bio_data ===")
for k in ('personal', 'education', 'military', 'awards', 'family'):
    print(f"  {k}: {len(bio.get(k, []))} items")
print(f"  timeline: {len(tl)} stages")

print("\n=== historical_notes ===")
print(f"  count: {len(hn)}")
for h in hn:
    title = h.get('title', '')
    content_len = len(str(h.get('content', '') or h.get('text', '')))
    print(f"  [{h.get('id')}] title={repr(title[:50])} content_len={content_len}")

c2 = ch02.get('content', '')
triple = re.findall(r'\*{3}.{10,200}\*{3}', c2)
vyk = 'выков' in c2.lower()
sym = 'символ' in c2.lower() and 'выков' in c2.lower()
dram = 'драм' in c2.lower() and 'валер' in c2.lower()
razdrazh = 'раздраж' in c2.lower()
print(f"\n=== ch_02 checks ===")
print(f"  triple-*** in content: {len(triple)}")
print(f"  выков: {vyk}  | выков+символ: {sym}")
print(f"  семейная драма+валера: {dram}")
print(f"  раздражалась: {razdrazh}")

# FC report
fc_files = glob.glob(f'{EXPORTS}/*phase_b_fc_report*.json')
if fc_files:
    fc = json.load(open(fc_files[0]))
    errors = fc.get('errors', [])
    warnings = fc.get('warnings', [])
    print(f"\n=== FC report: {len(errors)} errors, {len(warnings)} warnings ===")
    for item in errors + warnings:
        desc = item.get('what_is_written') or item.get('description') or ''
        print(f"  [{item.get('severity','?')}] {item.get('type','?')}: {str(desc)[:100]}")

# Patch: copy timeline from stage2
s2 = json.load(open(f'{RUN}/book_FINAL_stage2.json'))
book_s2 = s2.get('book_final') or s2
chs_s2 = book_s2.get('chapters', [])
ch01_s2 = next((c for c in chs_s2 if (c.get('id') or c.get('chapter_id')) == 'ch_01'), {})
timeline_s2 = ch01_s2.get('timeline') or []
hist_s2 = s2.get('historical_notes') or book_s2.get('historical_notes') or []

print(f"\n=== Stage2 data for patch ===")
print(f"  timeline: {len(timeline_s2)} stages")
print(f"  historical_notes: {len(hist_s2)} items")
for h in hist_s2:
    print(f"  [{h.get('id')}] {repr(h.get('title','')[:50])} content_len={len(str(h.get('content','') or h.get('text','')))}")

if len(tl) == 0 and len(timeline_s2) > 0:
    print("\nPatching timeline from stage2...")
    ch01['timeline'] = timeline_s2

has_content = any(h.get('content') or h.get('text') for h in hn)
if not has_content and len(hist_s2) > 0:
    print("Patching historical_notes from stage2...")
    if 'book_final' in pb:
        pb['historical_notes'] = hist_s2
    else:
        pb['historical_notes'] = hist_s2

pb_path = f'{RUN}/book_FINAL_phase_b_v31.json'
json.dump(pb, open(pb_path, 'w'), ensure_ascii=False, indent=2)
save_checkpoint('karakulina', 'proofreader', pb, auto_approve=True)
print("\nCheckpoint karakulina/proofreader updated (v31).")
