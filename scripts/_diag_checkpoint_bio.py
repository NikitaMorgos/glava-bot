import json
from pathlib import Path
sys_path = '/opt/glava'
import sys; sys.path.insert(0, sys_path)
from checkpoint_utils import load_checkpoint

# 1. Check what's in the proofreader checkpoint
cp = load_checkpoint('karakulina', 'proofreader', require_approved=True)
content = cp.get('content', {})
print(f"Checkpoint v{cp.get('version')} approved={bool(cp.get('approved_at'))}")
print(f"Content keys: {list(content.keys())[:8]}")

book = content.get('book_final') or content
chapters = book.get('chapters', [])
print(f"Chapters: {[c.get('id') or c.get('chapter_id') for c in chapters]}")

ch01 = next((c for c in chapters if (c.get('id') or c.get('chapter_id')) == 'ch_01'), {})
bio = ch01.get('bio_data') or {}
print(f"\nch_01.bio_data keys: {list(bio.keys())}")
for k in ('personal', 'education', 'military', 'awards', 'family'):
    print(f"  {k}: {len(bio.get(k, []))} items")

tl = ch01.get('timeline') or bio.get('timeline') or []
print(f"ch_01.timeline: {len(tl)} stages")

# 2. Check if gate 1 v2 log shows with_bio_block
log = Path('/tmp/v29_gate1_v2.log')
if log.exists():
    text = log.read_text(errors='replace')
    for line in text.split('\n'):
        if 'MODE' in line or 'with_bio_block' in line or 'acceptance_gate' in line:
            print('\n[LOG]', line[:100])
