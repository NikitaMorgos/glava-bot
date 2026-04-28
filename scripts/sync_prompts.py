#!/usr/bin/env python3
"""
sync_prompts.py — синхронизация актуальных промптов с сервера.

Скачивает с сервера все активные версии промптов (те, что прописаны
в pipeline_config.json как prompt_file) и сохраняет в prompts/.

Использование:
    python scripts/sync_prompts.py

Требования:
    - SSH-доступ к серверу по алиасу 'glava' (настроен в ~/.ssh/config)
    - Или: установить GLAVA_API_KEY и GLAVA_ADMIN_URL в окружении
      для загрузки через API (без SSH)
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT / "prompts"
CONFIG_FILE = PROMPTS_DIR / "pipeline_config.json"

SERVER_ALIAS = "glava"
SERVER_PROMPTS_PATH = "/opt/glava/prompts"

SKIP_KEYS = {"_comment", "_updated", "blitz_questions"}


def load_config() -> dict:
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)


def sync_via_ssh(active_files: list[str]) -> dict:
    """Скачивает файлы с сервера через scp. Возвращает {file: status}."""
    results = {}
    for filename in active_files:
        local_path = PROMPTS_DIR / filename
        remote_path = f"{SERVER_ALIAS}:{SERVER_PROMPTS_PATH}/{filename}"
        result = subprocess.run(
            ["scp", "-o", "ConnectTimeout=10", remote_path, str(local_path)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            size = local_path.stat().st_size // 1024
            results[filename] = f"OK скачан ({size} КБ)"
        else:
            results[filename] = f"FAIL: {result.stderr.strip()}"
    return results


def sync_via_api(active_files: list[str]) -> dict:
    """Скачивает промпты через Admin API (без SSH). Требует GLAVA_API_KEY."""
    try:
        import requests
    except ImportError:
        return {f: "❌ нет requests" for f in active_files}

    api_key = os.environ.get("GLAVA_API_KEY", "")
    base_url = os.environ.get("GLAVA_ADMIN_URL", "https://admin.glava.family")
    headers = {"X-Api-Key": api_key}

    # Маппинг filename → agent_key (из конфига)
    cfg = load_config()
    file_to_key = {
        v.get("prompt_file"): k
        for k, v in cfg.items()
        if k not in SKIP_KEYS and isinstance(v, dict) and v.get("prompt_file")
    }

    results = {}
    for filename in active_files:
        agent_key = file_to_key.get(filename)
        if not agent_key:
            results[filename] = "⚠️  агент не найден в конфиге"
            continue
        try:
            r = requests.get(f"{base_url}/api/prompts/{agent_key}", headers=headers, timeout=10)
            data = r.json()
            if not data.get("found"):
                results[filename] = "⚠️  промпт не найден на сервере"
                continue
            text = data.get("text", "")
            (PROMPTS_DIR / filename).write_text(text, encoding="utf-8")
            results[filename] = f"OK ({len(text)} chars)"
        except Exception as e:
            results[filename] = f"FAIL: {e}"
    return results


def main():
    if not CONFIG_FILE.exists():
        print(f"[ERROR] Конфиг не найден: {CONFIG_FILE}")
        sys.exit(1)

    cfg = load_config()

    # Собираем список активных prompt_file из конфига
    active_files = []
    for key, val in cfg.items():
        if key in SKIP_KEYS or not isinstance(val, dict):
            continue
        pf = val.get("prompt_file")
        if pf:
            active_files.append(pf)

    print(f"Активных промптов в конфиге: {len(active_files)}")
    for f in active_files:
        local = PROMPTS_DIR / f
        status = "OK (есть)" if local.exists() else "MISSING"
        print(f"  {f:45s} {status}")

    missing = [f for f in active_files if not (PROMPTS_DIR / f).exists()]
    if not missing:
        print("\nAll active prompts present locally. No sync needed.")
        return

    print(f"\nСкачиваю {len(missing)} недостающих файлов...")

    use_api = bool(os.environ.get("GLAVA_API_KEY"))
    if use_api:
        print("Метод: Admin API")
        results = sync_via_api(missing)
    else:
        print(f"Метод: SSH ({SERVER_ALIAS})")
        results = sync_via_ssh(missing)

    print("\nРезультат:")
    for filename, status in results.items():
        print(f"  {filename:45s} {status}")

    failed = [f for f, s in results.items() if s.startswith("❌")]
    if failed:
        print(f"\nWARNING: failed to download {len(failed)} files.")
        sys.exit(1)
    else:
        print(f"\nSync complete.")


if __name__ == "__main__":
    main()
