# -*- coding: utf-8 -*-
"""Добавляет favicon-теги в юридические страницы лендинга."""
import os

FAVICON_BLOCK = (
    '<!-- Favicons -->\n'
    '<link rel="icon" type="image/x-icon" href="./assets/favicon.ico">\n'
    '<link rel="icon" type="image/png" sizes="32x32" href="./assets/favicon-32.png">\n'
    '<link rel="icon" type="image/png" sizes="16x16" href="./assets/favicon-16.png">\n'
    '<link rel="apple-touch-icon" sizes="180x180" href="./assets/apple-touch-icon.png">\n'
)

landing = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'landing')
marker = '<link rel="stylesheet" href="./base.css">'

for fname in ['oferta.html', 'consent.html', 'policy.html']:
    path = os.path.join(landing, fname)
    with open(path, encoding='utf-8') as f:
        content = f.read()
    if 'favicon' not in content:
        content = content.replace(marker, FAVICON_BLOCK + marker)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated: {fname}')
    else:
        print(f'Already has favicons: {fname}')
