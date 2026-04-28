import json, glob, sys
sys.path.insert(0, '/opt/glava')
from checkpoint_utils import save_checkpoint

RUN = '/opt/glava/collab/runs/karakulina_v30_20260420_122027'

# Load stage2 book (has correct timeline + historical_notes with content)
s2 = json.load(open(f'{RUN}/book_FINAL_stage2.json'))
book_s2 = s2.get('book_final') or s2
chs_s2 = book_s2.get('chapters', [])
ch01_s2 = next((c for c in chs_s2 if (c.get('id') or c.get('chapter_id')) == 'ch_01'), {})
timeline_s2 = ch01_s2.get('timeline') or []
hist_s2 = s2.get('historical_notes') or book_s2.get('historical_notes') or []

print(f"Stage2 timeline: {len(timeline_s2)} stages")
print(f"Stage2 historical_notes: {len(hist_s2)} items")
for h in hist_s2:
    print(f"  [{h.get('id')}] title={repr(h.get('title','')[:50])} content_len={len(str(h.get('content','') or h.get('text','')))}")

# Load Phase B book
pb_path = f'{RUN}/book_FINAL_phase_b_v30.json'
pb = json.load(open(pb_path))
book_pb = pb.get('book_final') or pb
chs_pb = book_pb.get('chapters', [])
ch01_pb = next((c for c in chs_pb if (c.get('id') or c.get('chapter_id')) == 'ch_01'), {})

print(f"\nPhaseB timeline before: {len(ch01_pb.get('timeline') or [])}")
print(f"PhaseB historical_notes before: {len(pb.get('historical_notes', []))}")

# Patch: copy timeline from stage2
ch01_pb['timeline'] = timeline_s2

# Patch: copy historical_notes from stage2 (they have actual content)
if len(hist_s2) > 0 and any(h.get('content') or h.get('text') for h in hist_s2):
    if 'book_final' in pb:
        pb['historical_notes'] = hist_s2
    else:
        pb['historical_notes'] = hist_s2

print(f"\nAfter patch:")
print(f"  timeline: {len(ch01_pb.get('timeline') or [])} stages")
print(f"  historical_notes: {len(pb.get('historical_notes', []))} items")
for h in pb.get('historical_notes', []):
    print(f"  [{h.get('id')}] content_len={len(str(h.get('content','') or h.get('text','')))}")

# Save patched book
patched_path = f'{RUN}/book_FINAL_phase_b_v30_patched.json'
json.dump(pb, open(patched_path, 'w'), ensure_ascii=False, indent=2)
print(f"\nSaved: {patched_path}")

# Approve as checkpoint
save_checkpoint('karakulina', 'proofreader', pb, auto_approve=True)
print("Checkpoint karakulina/proofreader updated and approved.")

# Also overwrite main file
json.dump(pb, open(pb_path, 'w'), ensure_ascii=False, indent=2)
print(f"Updated: {pb_path}")
