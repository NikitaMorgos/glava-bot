"""
Wrapper: запустить test_stage1_pipeline для Каракулиной (v4 / промпт Даши v3.0).
Запускать: python scripts/_run_v4_karakulina.py
"""
import sys
import os

sys.argv = [
    "test_stage1_pipeline.py",
    "--transcript", "/opt/glava/transcript_karakulina_only.txt",
    "--character-name", "\u041a\u0430\u0440\u0430\u043a\u0443\u043b\u0438\u043d\u0430 \u0412\u0430\u043b\u0435\u043d\u0442\u0438\u043d\u0430 \u0418\u0432\u0430\u043d\u043e\u0432\u043d\u0430",
    "--output-dir", "/opt/glava/exports",
]

exec(open("/opt/glava/scripts/test_stage1_pipeline.py", encoding="utf-8").read())
