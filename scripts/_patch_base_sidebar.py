"""Вставляет ссылку на /dasha/stages в sidebar после pipeline_prompts."""
from pathlib import Path

BASE = Path("/opt/glava/admin/templates/base.html")
text = BASE.read_text(encoding="utf-8")

OLD = '''      <a href="/dasha/pipeline_prompts" class="sidebar-link {% if request.path.startswith('/dasha/pipeline_prompts') %}active{% endif %}">
        📄 Промпты пайплайна
      </a>'''

NEW = '''      <a href="/dasha/pipeline_prompts" class="sidebar-link {% if request.path.startswith('/dasha/pipeline_prompts') %}active{% endif %}">
        📄 Промпты пайплайна
      </a>
      <a href="/dasha/stages" class="sidebar-link {% if request.path.startswith('/dasha/stages') %}active{% endif %}">
        📋 Этапы пайплайна
      </a>'''

if "/dasha/stages" in text:
    print("Ссылка уже есть, пропускаю.")
elif OLD in text:
    BASE.write_text(text.replace(OLD, NEW), encoding="utf-8")
    print("Ссылка добавлена.")
else:
    print("ERROR: не нашёл якорный блок в base.html")
    print(repr(text[text.find("pipeline_prompts")-5:text.find("pipeline_prompts")+120]))
