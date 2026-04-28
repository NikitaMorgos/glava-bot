"""
Fix classify routing: if PDF integrity fail (too few pages) → escalate, don't silent accept.
"""
with open('/opt/glava/scripts/test_stage4_karakulina.py', 'r', encoding='utf-8') as f:
    src = f.read()

OLD = '''        if builder_issues and not layout_issues:
            print(f"\\n✅ QA issues are builder-only ({len(builder_issues)}) — принимаем PDF, логируем как tech debt")
            for bi in builder_issues:
                print(f"  [builder] {bi.get('type','?')}: {str(bi.get('description',''))[:80]}")
            final_verdict = "pass"  # treat as accepted
            break'''

NEW = '''        if builder_issues and not layout_issues:
            # Check if there are critical integrity issues (e.g. PDF too few pages)
            critical_builder = [i for i in builder_issues if i.get("severity") == "critical"]
            if critical_builder:
                print(f"\\n⚠️  Builder-only issues but CRITICAL ({len(critical_builder)}) — loggin as tech debt but continuing to next iteration if any")
                for bi in critical_builder:
                    print(f"  [builder/critical] {bi.get('type','?')}: {str(bi.get('description',''))[:80]}")
                # Still break — layout_designer cannot fix builder issues
                final_verdict = "fail"
                break
            else:
                print(f"\\n✅ QA issues are builder-only non-critical ({len(builder_issues)}) — принимаем PDF, логируем как tech debt")
                for bi in builder_issues:
                    print(f"  [builder] {bi.get('type','?')}: {str(bi.get('description',''))[:80]}")
                final_verdict = "pass"  # treat as accepted
                break'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("Routing escalation patch applied OK")
else:
    print("ERROR: pattern not found!")

with open('/opt/glava/scripts/test_stage4_karakulina.py', 'w', encoding='utf-8') as f:
    f.write(src)

import subprocess
r = subprocess.run(['python3', '-m', 'py_compile',
                   '/opt/glava/scripts/test_stage4_karakulina.py'],
                  capture_output=True, text=True)
print("Syntax:", "OK" if r.returncode == 0 else r.stderr)
