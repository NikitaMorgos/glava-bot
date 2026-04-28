#!/usr/bin/env python3
"""
Complete PDF builder: finds ALL font names used in layout code,
registers system font aliases for all of them, then generates PDF.
Tries iter1 first (simpler), falls back to iter3.
"""
import re
import sys
import pathlib
import subprocess

EXPORTS_DIR = pathlib.Path("/opt/glava/exports")

SERIF       = "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"
SERIF_BOLD  = "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf"
SERIF_ITAL  = "/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf"
SANS        = "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
SANS_BOLD   = "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"

def pick_font(name: str) -> str:
    n = name.lower()
    if "bold" in n: return SERIF_BOLD
    if "italic" in n or n.endswith("-it") or n.endswith("-i"): return SERIF_ITAL
    if any(x in n for x in ("serif","playfair","cormorant","merriweather","garamond","libre","georgia","times")):
        return SERIF
    return SANS

def patch_code(code: str, output_pdf: str) -> str:
    # 1. pt import
    for bad in [
        "from reportlab.lib.units import mm, pt",
        "from reportlab.lib.units import pt, mm",
        "from reportlab.lib.units import mm,pt",
    ]:
        code = code.replace(bad, "from reportlab.lib.units import mm\npt = 1")

    # 2. Find all font names
    all_fonts = set(re.findall(r"""(?:setFont|fontName)\s*[=(]\s*['"]([^'"]+)['"]""", code))
    print(f"  Fonts: {sorted(all_fonts)}")

    reg_lines = [
        "from reportlab.pdfbase import pdfmetrics",
        "from reportlab.pdfbase.ttfonts import TTFont",
        "import os as _os",
        "",
    ]
    for f in sorted(all_fonts):
        path = pick_font(f)
        reg_lines.append(f"if _os.path.exists({path!r}):")
        reg_lines.append(f"    try: pdfmetrics.registerFont(TTFont({f!r}, {path!r}))")
        reg_lines.append("    except Exception: pass")
    font_block = "\n".join(reg_lines)

    # Replace font registration block
    pattern = r"# Регистрация шрифтов.*?(?=\n\n\S|\nclass |\ndef [a-z]|\n# ─)"
    if re.search(pattern, code, flags=re.DOTALL):
        code = re.sub(pattern, font_block, code, count=1, flags=re.DOTALL)
    else:
        # Insert after imports section (after last "import" line)
        lines = code.split("\n")
        last_import = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                last_import = i
        lines.insert(last_import + 1, "\n" + font_block + "\n")
        code = "\n".join(lines)

    # 3. ReportLab method aliases
    code = code.replace(".drawCentredText(", ".drawCentredString(")
    code = code.replace(".drawRightText(",   ".drawRightString(")

    # 4. Photo paths
    code = code.replace("'karakulina_photos/",  "'/opt/glava/exports/karakulina_photos/")
    code = code.replace('"karakulina_photos/',  '"/opt/glava/exports/karakulina_photos/')

    # 5. Output PDF path
    code = re.sub(
        r"filename\s*=\s*['\"][^'\"]*\.pdf['\"]",
        f"filename = '{output_pdf}'",
        code,
    )

    return code


# Try iter1, then iter2, then iter3
candidates = []
for n in [1, 2, 3]:
    candidates += sorted(EXPORTS_DIR.glob(f"karakulina_iter{n}_layout_code_*.py"))

if not candidates:
    print("[ERROR] No layout code found")
    sys.exit(1)

output_pdf = str(EXPORTS_DIR / "karakulina_biography.pdf")
succeeded = False

for src in candidates:
    print(f"\n[TRY] {src.name}")
    code = src.read_text(encoding="utf-8")
    patched = patch_code(code, output_pdf)

    out = EXPORTS_DIR / "karakulina_layout_PATCHED.py"
    out.write_text(patched, encoding="utf-8")

    result = subprocess.run(
        ["python3", str(out)],
        capture_output=True, text=True, cwd=str(EXPORTS_DIR)
    )
    if result.stdout:
        print(result.stdout)

    pdf = EXPORTS_DIR / "karakulina_biography.pdf"
    if pdf.exists():
        print(f"[OK] PDF: {pdf} ({pdf.stat().st_size:,} bytes)")
        succeeded = True
        break
    else:
        # Show last error
        lines = (result.stderr or "").strip().splitlines()
        print(f"[FAIL] " + (lines[-1] if lines else "unknown error"))

if not succeeded:
    print("\n[ERROR] All candidates failed")
    # Show full stderr of last attempt
    print(result.stderr[-2000:])
    sys.exit(1)
