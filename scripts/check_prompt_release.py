#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_prompt_release.py — guard для ритуала релизов промптов.

Правила:
  1) Один релиз = изменение максимум одного prompt *.md
  2) Должен быть затронут prompts/pipeline_config.json
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _git_changed_files() -> list[str]:
    cmd = ["git", "status", "--porcelain"]
    run = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if run.returncode != 0:
        raise RuntimeError(run.stderr.strip() or "git status failed")
    files = []
    for line in (run.stdout or "").splitlines():
        if len(line) < 4:
            continue
        files.append(line[3:].strip())
    return files


def main() -> int:
    changed = _git_changed_files()
    prompt_md = [f for f in changed if f.startswith("prompts/") and f.endswith(".md")]
    config_changed = "prompts/pipeline_config.json" in changed

    unique_prompt_md = sorted(set(prompt_md))
    ok_one_prompt = len(unique_prompt_md) <= 1
    ok_config = config_changed
    passed = ok_one_prompt and ok_config

    print("[PROMPT_RELEASE_GUARD]")
    print(f"  changed_prompt_files: {len(unique_prompt_md)}")
    for p in unique_prompt_md:
        print(f"    - {p}")
    print(f"  pipeline_config_changed: {ok_config}")
    print(f"  passed: {passed}")

    if not ok_one_prompt:
        print("  FAIL: изменено более одного prompt *.md (нарушен one change-set).")
    if not ok_config:
        print("  FAIL: не изменён prompts/pipeline_config.json.")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
