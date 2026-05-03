#!/usr/bin/env python3
"""Check bio_data.family in proofreader checkpoint."""
import json

with open('/opt/glava/checkpoints/karakulina/proofreader.json', encoding='utf-8') as f:
    data = json.load(f)

# Find ch_01 bio_data
book = data.get('book', data)
chapters = book.get('chapters', [])
print(f"Total chapters: {len(chapters)}")

for ch in chapters:
    chid = ch.get('id','?')
    bio = ch.get('bio_data', {})
    if bio:
        family = bio.get('family', [])
        personal = bio.get('personal', [])
        print(f"\nCh {chid} bio_data:")
        print(f"  family ({len(family)} entries):")
        for item in family:
            if isinstance(item, dict):
                print(f"    {item.get('label','?')}: {item.get('value','?')}")
            else:
                print(f"    {item}")
        print(f"  personal ({len(personal)} entries):")
        for item in personal[:3]:
            if isinstance(item, dict):
                print(f"    {item.get('label','?')}: {item.get('value','?')}")

# Also check top-level
if not chapters:
    print("No chapters found in checkpoint")
    print("Top-level keys:", list(data.keys())[:10])
