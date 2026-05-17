import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from pipeline_utils import parse_pin_list_from_markdown

out = Path('collab/runs/karakulina_v58')

# Check the actual book's bio_data.timeline
book = json.loads((out / 'karakulina_book_FINAL_20260517_131012.json').read_text('utf-8'))
ch01 = next((ch for ch in book.get('chapters', []) if ch.get('id') == 'ch_01'), None)
if ch01:
    bio = ch01.get('bio_data', {})
    timeline = bio.get('timeline', [])
    print(f'bio_data.timeline has {len(timeline)} periods:')
    for p in timeline:
        print(f'  {p.get("title", "?")[:80]}')
else:
    print('ch_01 not found')

print()
# Check the parsed pin_list
pin = parse_pin_list_from_markdown('collab/context/known_episodes_karakulina.md')
print(f'Pin list parsed: {len(pin["episodes"])} episodes, {len(pin["bytovye"])} bytovye, {len(pin["traits"])} traits')
print('First 5 episodes:')
for ep in pin["episodes"][:5]:
    print(f'  {ep}')
print('First 5 bytovye:')
for b in pin["bytovye"][:5]:
    print(f'  {b}')
