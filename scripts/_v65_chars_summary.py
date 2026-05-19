#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v65: distribution gate chars summary (sum of chapter content, NOT file_size)."""
import json, sys, glob
sys.stdout.reconfigure(encoding='utf-8')

book_files = sorted(glob.glob('exports/stage3_v65/karakulina_book_FINAL_stage3_*.json'), reverse=True)
book_raw = json.load(open(book_files[0], encoding='utf-8'))
book = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw

chapters = book.get('chapters', [])
ch_chars = {}
total_content_chars = 0
for ch in chapters:
    cid = ch.get('id', '?')
    c = ch.get('content') or ''
    if cid == 'ch_01' and not c:
        # ch_01 uses bio_data structure — render it for char count
        bio = ch.get('bio_data', {})
        c = json.dumps(bio, ensure_ascii=False)
    ch_chars[cid] = len(c)
    total_content_chars += len(c)

hist_notes = book.get('historical_notes', [])
hist_chars = sum(len(str(n)) for n in hist_notes)

print(f"\n=== Distribution Gate Check (chars = sum of chapter content, NOT file_size) ===")
print(f"Total content chars: {total_content_chars} ({'OK' if total_content_chars >= 20000 else 'FAIL'} >=20000)")
print(f"ch_01 (paspart): {ch_chars.get('ch_01', 0)} chars (~3000 target)")
ch02 = ch_chars.get('ch_02', 0)
ch03 = ch_chars.get('ch_03', 0)
ch04 = ch_chars.get('ch_04', 0)
epil = ch_chars.get('epilogue', 0)
narrative = ch02 + ch03 + ch04 + epil
print(f"Narrative (ch02+ch03+ch04+epilogue): {narrative} ({'OK' if narrative >= 15000 else 'FAIL'} >=15000)")
print(f"ch_02: {ch02} ({'OK' if ch02 >= 7000 else 'BELOW'} >=7K)")
print(f"ch_03: {ch03} ({'OK' if ch03 >= 4000 else 'BELOW'} >=4K)")
print(f"ch_04: {ch04} ({'OK' if ch04 >= 2500 else 'BELOW'} >=2.5K)")
print(f"epilogue: {epil} ({'OK' if 800 <= epil <= 1500 else 'CHECK'} 800-1500)")
print(f"historical_notes (field): {hist_chars} chars, {len(hist_notes)} notes ({'OK' if len(hist_notes) >= 3 else 'BELOW'} >=3)")
print(f"Total with hist_notes: {total_content_chars + hist_chars}")
