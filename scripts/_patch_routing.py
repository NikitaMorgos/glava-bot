"""Patch orchestrator: add classify_issue_owner routing in QA loop."""

with open('/opt/glava/scripts/test_stage4_karakulina.py', 'r', encoding='utf-8') as f:
    src = f.read()

OLD = """        if qa_iteration >= MAX_QA_ITERATIONS:
            print(f"\\n⚠️  QA FAIL после {MAX_QA_ITERATIONS} итераций — эскалация к Продюсеру (не реализована в тесте)")
            break

        # Готовим issues для следующей итерации
        previous_qa_issues = qa_result.get("issues", [])
        print(f"\\n🔄 QA FAIL — передаём Верстальщику на доработку (итерация {qa_iteration + 1})")"""

NEW = """        if qa_iteration >= MAX_QA_ITERATIONS:
            print(f"\\n⚠️  QA FAIL после {MAX_QA_ITERATIONS} итераций — эскалация к Продюсеру (не реализована в тесте)")
            break

        # Classify issues by owner (spec v4: routing builder vs layout_designer)
        all_issues = qa_result.get("issues", [])
        layout_issues = [i for i in all_issues if classify_issue_owner(i) == "layout_designer"]
        builder_issues = [i for i in all_issues if classify_issue_owner(i) == "builder"]

        if builder_issues and not layout_issues:
            print(f"\\n✅ QA issues are builder-only ({len(builder_issues)}) — принимаем PDF, логируем как tech debt")
            for bi in builder_issues:
                print(f"  [builder] {bi.get('type','?')}: {str(bi.get('description',''))[:80]}")
            final_verdict = "pass"  # treat as accepted
            break

        if layout_issues:
            print(f"\\n[QA] Layout issues: {len(layout_issues)}, Builder issues: {len(builder_issues)} (not forwarded to Layout Designer)")
            qa_result = {**qa_result, "issues": layout_issues}

        # Готовим issues для следующей итерации
        previous_qa_issues = qa_result.get("issues", [])
        print(f"\\n🔄 QA FAIL — передаём Верстальщику на доработку (итерация {qa_iteration + 1})")"""

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("Routing patch applied OK")
else:
    print("ERROR: pattern not found!")
    # Show nearby context
    idx = src.find('MAX_QA_ITERATIONS')
    print("MAX_QA_ITERATIONS context:", repr(src[idx:idx+300]))

with open('/opt/glava/scripts/test_stage4_karakulina.py', 'w', encoding='utf-8') as f:
    f.write(src)

import subprocess
r = subprocess.run(['python3', '-m', 'py_compile',
                   '/opt/glava/scripts/test_stage4_karakulina.py'],
                  capture_output=True, text=True)
print("Syntax:", "OK" if r.returncode == 0 else r.stderr)
