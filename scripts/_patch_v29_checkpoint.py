"""
Patch v29 Phase B book:
1. Copy ch_01.timeline from Stage2 book to Phase B book
2. Copy top-level historical_notes from Stage2 to Phase B
3. Approve patched book as new proofreader checkpoint v9
"""
import json, sys
from pathlib import Path
sys.path.insert(0, '/opt/glava')
from checkpoint_utils import save_checkpoint

RUN_DIR = Path('/opt/glava/exports/karakulina_v29_run_20260420_072506')

# Load Stage2 book (has ch_01.timeline)
s2_path = RUN_DIR / 'karakulina_book_FINAL_20260420_072948.json'
data_s2 = json.loads(s2_path.read_text(encoding='utf-8'))
book_s2 = data_s2.get('book_final') or data_s2
ch01_s2 = next((c for c in book_s2['chapters'] if (c.get('id') or c.get('chapter_id')) == 'ch_01'), {})
timeline_s2 = ch01_s2.get('timeline', [])
hist_notes_s2 = data_s2.get('historical_notes', [])
print(f"Stage2: ch_01.timeline={len(timeline_s2)} stages, historical_notes={len(hist_notes_s2)}")
for t in timeline_s2[:3]:
    print(f"  {t.get('period','?')}: {t.get('title','?')[:50]}")

# Load Phase B book
pb_path = sorted(RUN_DIR.glob('karakulina_v29_book_FINAL_phase_b_*.json'))[0]
data_pb = json.loads(pb_path.read_text(encoding='utf-8'))
book_pb = data_pb.get('book_final') or data_pb

# Patch: copy timeline to ch_01 and historical_notes top-level
patched = data_pb.copy()
book_pb_patched = patched if 'chapters' in patched else patched.get('book_final', patched)

# Find ch_01 and patch timeline
for ch in book_pb_patched.get('chapters', []):
    cid = ch.get('id') or ch.get('chapter_id')
    if cid == 'ch_01':
        if not ch.get('timeline') and timeline_s2:
            ch['timeline'] = timeline_s2
            print(f"[PATCH] ch_01.timeline: added {len(timeline_s2)} stages from Stage2")

# Copy historical_notes from Stage2 to Phase B (even if empty, preserves structure)
if hist_notes_s2 and not patched.get('historical_notes'):
    patched['historical_notes'] = hist_notes_s2
    print(f"[PATCH] historical_notes: copied {len(hist_notes_s2)} items from Stage2")

# Save patched book
patched_path = RUN_DIR / 'karakulina_v29_book_FINAL_phase_b_patched.json'
patched_path.write_text(json.dumps(patched, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"[SAVED] patched: {patched_path.name}")

# Verify
ch01_pb = next((c for c in book_pb_patched.get('chapters', []) 
                if (c.get('id') or c.get('chapter_id')) == 'ch_01'), {})
print(f"\nVerify patched Phase B ch_01.timeline: {len(ch01_pb.get('timeline') or [])}")
print(f"Verify patched historical_notes: {len(patched.get('historical_notes', []))}")

# Approve as proofreader checkpoint v9
book_to_approve = patched
save_checkpoint('karakulina', 'proofreader', book_to_approve, auto_approve=True,
                source_file=str(patched_path))
print("\n[CHECKPOINT] Saved+approved karakulina/proofreader checkpoint (v29, patched Phase B)")

# Also save the collab copy
collab_run_file = Path('/opt/glava/exports/karakulina_v29_last_collab_run.txt')
if collab_run_file.exists():
    collab_run = Path(collab_run_file.read_text().strip())
    if collab_run.exists():
        import shutil
        shutil.copy(patched_path, collab_run / 'book_FINAL_phase_b_v29.json')
        print(f"[COLLAB] Updated book_FINAL_phase_b_v29.json in {collab_run.name}")
