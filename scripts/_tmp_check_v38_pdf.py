import json, sys, os
sys.path.insert(0, "/opt/glava")
sys.path.insert(0, "/opt/glava/scripts")

import glob

# Find the v38 gate2c pdf
pdfs = sorted(glob.glob("/opt/glava/exports/karakulina_v38_stage4_gate_2c_*.pdf"))
if not pdfs:
    print("NO PDF FOUND")
    sys.exit(1)

pdf_path = pdfs[-1]
print("PDF:", pdf_path)
size_kb = os.path.getsize(pdf_path) // 1024
print(f"Size: {size_kb} KB")

# Check book source for expected char count
book_path = "/opt/glava/exports/stage3_v38/karakulina_v38_book_FINAL_stage3_20260430_120653.json"
with open(book_path) as f:
    book = json.load(f)
book_chars = sum(len(ch.get("content", "")) for ch in book.get("chapters", []))
print(f"Book chars (chapters content only): {book_chars}")

import pdfplumber
with pdfplumber.open(pdf_path) as pdf:
    pages_count = len(pdf.pages)
    all_text = "\n".join(p.extract_text() or "" for p in pdf.pages)

all_text_flat = " ".join(all_text.split())
char_count = len(all_text_flat)
print(f"Pages in PDF: {pages_count}")
print(f"Characters extracted: {char_count}")
print(f"Coverage vs book: {char_count/max(book_chars,1)*100:.1f}%")
print(f"First 300 chars: {all_text_flat[:300]}")
print("---")
print(f"Last 200 chars: ...{all_text_flat[-200:]}")

# Verdict
if char_count >= 10000:
    print(f"\nPASS: {char_count} chars — full content in PDF")
else:
    print(f"\nFAIL: only {char_count} chars — content loss!")

# Check fidelity from log
import subprocess
res = subprocess.run(
    ["grep", "-E", "FIDELITY|Refs:|book_final unwrapped|WARN.*photos", "/tmp/v38_stage4_gate2c.log"],
    capture_output=True, text=True
)
print("\n--- Key log lines ---")
print(res.stdout)
