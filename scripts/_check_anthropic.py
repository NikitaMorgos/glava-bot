"""Быстрая проверка Anthropic API: ключ и доступные модели."""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import anthropic

key = os.environ.get("ANTHROPIC_API_KEY", "")
print(f"API key: {key[:12]}...{key[-4:]} (len={len(key)})")

client = anthropic.Anthropic(api_key=key)

# Тест с реальным минимальным запросом
for model in [
    "claude-sonnet-4-20250514",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-haiku-4-5-20251001",
]:
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=10,
            messages=[{"role": "user", "content": "1+1=?"}],
        )
        print(f"  OK   {model}")
        break
    except anthropic.PermissionDeniedError as e:
        print(f"  403  {model}: {e}")
    except anthropic.NotFoundError as e:
        print(f"  404  {model}: {e}")
    except Exception as e:
        print(f"  ERR  {model}: {type(e).__name__}: {e}")
