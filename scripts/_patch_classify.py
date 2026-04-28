"""
Patch test_stage4_karakulina.py:
1. Add classify_issue_owner() and routing logic
2. Fix Cover Designer Replicate skip when --use-existing-cover
"""
import re

with open('/opt/glava/scripts/test_stage4_karakulina.py', 'r', encoding='utf-8') as f:
    src = f.read()

# ── Fix 1: classify_issue_owner() ────────────────────────────────
# Insert after the _build_msg_content function

CLASSIFY_CODE = '''
# ── Issue owner classification (from spec v4) ───────────────────
LAYOUT_DESIGNER_ISSUES = {
    "photo_wrong_page", "photo_wrong_layout", "callout_wrong_position",
    "chapter_wrong_page", "photo_missing", "element_order_wrong",
}
BUILDER_ISSUES = {
    "pagination", "toc_page_numbers", "font_not_embedded", "font_rendering",
    "margin_overflow", "orphan_widow", "photo_not_loaded", "headers_footers",
    "toc", "page_numbers",
}

def classify_issue_owner(issue: dict) -> str:
    """Returns 'layout_designer' or 'builder' for a QA issue."""
    if issue.get("owner"):
        return issue["owner"]
    itype = issue.get("type", "").lower()
    # Check checklist keys that map to builder
    if itype in BUILDER_ISSUES:
        return "builder"
    if itype in LAYOUT_DESIGNER_ISSUES:
        return "layout_designer"
    # Heuristic: rendering/font/margin keywords → builder
    desc = (issue.get("description", "") + " " + itype).lower()
    for kw in ("шрифт", "font", "номер", "numer", "paginat", "toc", "оглавлени",
               "колонтитул", "header", "footer", "margin", "поле"):
        if kw in desc:
            return "builder"
    return "layout_designer"


'''

# Insert before "async def call_agent"
src = src.replace('async def call_agent(', CLASSIFY_CODE + 'async def call_agent(', 1)

# ── Fix 2: Routing in QA loop ────────────────────────────────────
# Find the block after QA result validation where we decide what to do
# Current: always passes qa_result back to layout_designer
# New: classify issues and only pass layout issues to layout_designer

OLD_ROUTING = '''        if qa_result.get("verdict") == "pass":
            break

        previous_qa_issues = qa_result.get("issues", [])'''

NEW_ROUTING = '''        if qa_result.get("verdict") == "pass":
            break

        # Classify issues by owner (spec v4: §Маршрутизация ошибок QA)
        all_issues = qa_result.get("issues", [])
        layout_issues = [i for i in all_issues if classify_issue_owner(i) == "layout_designer"]
        builder_issues = [i for i in all_issues if classify_issue_owner(i) == "builder"]

        if builder_issues and not layout_issues:
            # All issues are builder-only — no point iterating Layout Designer
            print(f"[QA] Builder-only issues ({len(builder_issues)}) — accepted as tech debt, not re-sending to Layout Designer")
            for bi in builder_issues:
                print(f"  [builder] {bi.get('type','?')}: {bi.get('description','')[:80]}")
            break  # Accept PDF, log as tech debt

        if layout_issues:
            print(f"[QA] Layout issues: {len(layout_issues)}, Builder issues: {len(builder_issues)} (not forwarded)")
            qa_result = {**qa_result, "issues": layout_issues}

        previous_qa_issues = qa_result.get("issues", [])'''

if OLD_ROUTING in src:
    src = src.replace(OLD_ROUTING, NEW_ROUTING, 1)
    print("Routing patch applied OK")
else:
    # Try to find and show context around "verdict" == "pass"
    idx = src.find('"verdict") == "pass"')
    if idx != -1:
        print("Found verdict check at:", idx)
        print("Context:", repr(src[idx-100:idx+200]))
    else:
        print("WARNING: Could not find routing insertion point")

# ── Fix 3: Cover Designer — skip Replicate when --use-existing-cover ──
# Find where Replicate is called and add a guard
OLD_REPLICATE = '''    if args.use_existing_cover:
        cover_portrait = Path(args.use_existing_cover).read_bytes()
        print(f"[COVER] Используем предзагруженный портрет, пропускаем Replicate")
    else:'''

# Check if this pattern exists; if not, find a similar one
if OLD_REPLICATE in src:
    print("Replicate skip pattern found - already correct")
else:
    # Find the Replicate call and check if there's a guard
    replicate_idx = src.find('Replicate')
    if replicate_idx != -1:
        print("Replicate found at:", replicate_idx)
        print("Context:", repr(src[replicate_idx-200:replicate_idx+100]))

with open('/opt/glava/scripts/test_stage4_karakulina.py', 'w', encoding='utf-8') as f:
    f.write(src)

# Verify syntax
import subprocess
result = subprocess.run(['python3', '-m', 'py_compile',
                       '/opt/glava/scripts/test_stage4_karakulina.py'],
                      capture_output=True, text=True)
if result.returncode == 0:
    print("Syntax OK")
else:
    print("SYNTAX ERROR:", result.stderr)
