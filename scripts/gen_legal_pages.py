# -*- coding: utf-8 -*-
"""Генерирует HTML-страницы для юридических документов в папке landing/."""
import json
import os

with open(r'c:\Users\user\Downloads\docs_parsed.json', encoding='utf-8') as f:
    data = json.load(f)

FONT_URL = "https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Work+Sans:wght@300..700&display=swap"

def is_heading(text):
    return len(text) < 90 and (
        text[0].isdigit() or text.isupper() or
        text.startswith('ДОГОВОР') or text.startswith('СОГЛАСИЕ') or text.startswith('ПОЛИТИКА')
    )

def make_html(title, paragraphs):
    lines = []
    for p in paragraphs:
        p_esc = p.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        if is_heading(p):
            lines.append(f'<h2>{p_esc}</h2>')
        else:
            lines.append(f'<p>{p_esc}</p>')
    body = '\n    '.join(lines)
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Глава</title>
<link rel="stylesheet" href="./base.css">
<link rel="stylesheet" href="./style.css">
<link href="{FONT_URL}" rel="stylesheet">
<style>
  .doc-page {{ max-width: 800px; margin: 0 auto; padding: 40px 24px 80px; }}
  .doc-page h1 {{ font-family: 'Instrument Serif', serif; font-size: 1.8rem; margin-bottom: 8px; line-height: 1.3; }}
  .doc-page h2 {{ font-family: 'Work Sans', sans-serif; font-size: 0.95rem; font-weight: 600;
    margin-top: 28px; margin-bottom: 8px; text-transform: none; letter-spacing: 0; }}
  .doc-page p {{ font-size: 0.875rem; line-height: 1.75; margin-bottom: 8px; }}
  .doc-back {{ display: inline-block; margin-bottom: 32px; font-size: 0.85rem; text-decoration: none;
    opacity: 0.6; }}
  .doc-back:hover {{ opacity: 1; text-decoration: underline; }}
  .doc-date {{ font-size: 0.8rem; opacity: 0.5; margin-bottom: 32px; }}
</style>
</head>
<body>
<div class="doc-page">
  <a href="./" class="doc-back">← Назад на главную</a>
  <h1>{title}</h1>
  {body}
</div>
</body>
</html>"""

pages = [
    ('oferta',  'Договор-оферта'),
    ('consent', 'Согласие на обработку персональных данных'),
    ('policy',  'Политика обработки персональных данных'),
]

landing = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'landing')

for key, title in pages:
    html = make_html(title, data[key])
    path = os.path.join(landing, f'{key}.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'Created: {path}')
