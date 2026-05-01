import json, sys
sys.path.insert(0, "/opt/glava")
sys.path.insert(0, "/opt/glava/scripts")

import glob
# Find the pdf
pdfs = sorted(glob.glob("/opt/glava/exports/karakulina_v38_fix023_*.pdf"))
if not pdfs:
    print("NO PDF FOUND")
    sys.exit(1)

pdf_path = pdfs[-1]
print("PDF:", pdf_path)

import os
size_kb = os.path.getsize(pdf_path) // 1024
print(f"Size: {size_kb} KB")

try:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        pages_count = len(pdf.pages)
        all_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    all_text_flat = " ".join(all_text.split())
    char_count = len(all_text_flat)
    print(f"Pages: {pages_count}")
    print(f"Characters (flat): {char_count}")
    print(f"First 500 chars: {all_text_flat[:500]}")
    print("---")
    print(f"Last 300 chars: ...{all_text_flat[-300:]}")

    # Expect >= 10000 chars (was 1059 before fix)
    if char_count >= 10000:
        print(f"\nPASS: {char_count} chars >= 10000 (was 1059 before fix)")
    else:
        print(f"\nFAIL: {char_count} chars < 10000 — still losing content!")

except ImportError:
    print("pdfplumber not available — checking size only")
    if size_kb >= 100:
        print(f"PASS (size-based): {size_kb} KB")
    else:
        print(f"FAIL (size-based): {size_kb} KB — too small")
