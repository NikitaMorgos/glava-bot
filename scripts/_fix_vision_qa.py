"""Fix test_stage4_karakulina.py:
1. Replace corrupted _build_msg_content helper with correct version
2. Fix _vision_images usage in run_layout_qa
3. Increase DPI to 120, 4 pages
"""
import re

with open('/opt/glava/scripts/test_stage4_karakulina.py', 'r', encoding='utf-8') as f:
    src = f.read()

# ── Fix 1: Replace the corrupted helper function ──────────────────
# Find the corrupted version and replace with correct one
bad_helper_pattern = r'def _build_msg_content\(user_message: dict\):.*?(?=\nasync def call_agent)'
good_helper = '''def _build_msg_content(user_message: dict):
    """Build Anthropic messages content: text + optional vision image blocks."""
    vision_images = user_message.pop("_vision_images", None)
    text_part = json.dumps(user_message, ensure_ascii=False)
    if not vision_images:
        return text_part
    content = [{"type": "text", "text": text_part}]
    for img in vision_images:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": img["media_type"],
                "data": img["data"],
            },
        })
    return content


'''

src = re.sub(bad_helper_pattern, good_helper, src, flags=re.DOTALL)

# ── Fix 2: ensure _vision_images injection in run_layout_qa ──────
# Remove pdf_previews from data dict if still there
if '"pdf_previews": pdf_previews' in src:
    src = src.replace(
        '**({"pdf_previews": pdf_previews} if pdf_previews else {}),\n        }\n    }',
        '        }\n    }\n    if pdf_previews:\n        user_message["_vision_images"] = pdf_previews'
    )

# ── Fix 3: DPI and pages ──────────────────────────────────────────
src = src.replace(
    'dpi=72, first_page=1, last_page=3',
    'dpi=120, first_page=1, last_page=4'
)
src = src.replace(
    'dpi=72, first_page=1, last_page=4',
    'dpi=120, first_page=1, last_page=4'
)

with open('/opt/glava/scripts/test_stage4_karakulina.py', 'w', encoding='utf-8') as f:
    f.write(src)

# Verify
with open('/opt/glava/scripts/test_stage4_karakulina.py', 'r', encoding='utf-8') as f:
    result = f.read()

assert 'def _build_msg_content' in result
assert '"""Build Anthropic messages content' in result
assert 'dpi=120' in result
assert '"_vision_images"' in result
print('All fixes applied OK')
