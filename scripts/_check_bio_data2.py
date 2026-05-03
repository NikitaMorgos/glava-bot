#!/usr/bin/env python3
"""Check bio_data.family in proofreader checkpoint (nested content)."""
import json

with open('/opt/glava/checkpoints/karakulina/proofreader.json', encoding='utf-8') as f:
    data = json.load(f)

content = data.get('content', {})
if isinstance(content, str):
    content = json.loads(content)

print("Content keys:", list(content.keys())[:15])
chapters = content.get('chapters', [])
print(f"Total chapters: {len(chapters)}")

for ch in chapters:
    chid = ch.get('id','?')
    bio = ch.get('bio_data', {})
    if bio:
        family = bio.get('family', [])
        print(f"\nCh {chid} bio_data.family ({len(family)} entries):")
        for item in family[:10]:
            if isinstance(item, dict):
                print(f"  {item.get('label','?')}: {item.get('value','?')[:80]}")
            else:
                print(f"  {str(item)[:80]}")
    else:
        paragraphs = ch.get('paragraphs', [])
        print(f"Ch {chid}: {len(paragraphs)} paragraphs, no bio_data")
