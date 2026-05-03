#!/usr/bin/env python3
"""Check ghostwriter checkpoint for bio_data.family."""
import json

# Load ghostwriter checkpoint
with open('/opt/glava/checkpoints/karakulina/ghostwriter.json', encoding='utf-8') as f:
    data = json.load(f)

content = data.get('content', data)
if isinstance(content, str):
    content = json.loads(content)

print("Keys:", list(content.keys())[:15])
chapters = content.get('chapters', [])
print(f"Total chapters: {len(chapters)}")

for ch in chapters:
    chid = ch.get('id','?')
    bio = ch.get('bio_data', {})
    paragraphs = ch.get('paragraphs', [])
    print(f"\nCh {chid}: {len(paragraphs)} paragraphs")
    if bio:
        family = bio.get('family', [])
        print(f"  bio_data.family ({len(family)} entries):")
        for item in family[:10]:
            if isinstance(item, dict):
                print(f"    {item.get('label','?')}: {str(item.get('value','?'))[:80]}")
            else:
                print(f"    {str(item)[:80]}")
    else:
        print(f"  no bio_data")
