"""
Превращает blocks_json (структуру книги от glava pipeline или после правок в
редакторе) в самодостаточный HTML, из которого cabinet.pdf_render делает PDF.

Не пытается быть точной копией мастер-верстки от glava — это лёгкий рендер
"клиентских правок": простая, читабельная A5-типографика без внешних ассетов.
Фотоблоки пока рендерятся как placeholder — полноценные фото (с реальными
файлами) появятся, когда мы будем скачивать photos из S3 в шаге F.
"""

from __future__ import annotations

import html
from typing import Any


def _esc(text: Any) -> str:
    if text is None:
        return ""
    return html.escape(str(text))


def _render_block(b: dict, photos_map: dict | None = None) -> str:
    t = (b.get("type") or "").strip()
    if t == "paragraph":
        return f"<p>{_esc(b.get('text', '')).replace(chr(10), '<br>')}</p>"
    if t == "subsection_title":
        return f"<h3>{_esc(b.get('title') or b.get('text', ''))}</h3>"
    if t == "pull_quote":
        text = _esc(b.get("text", ""))
        attr = b.get("attribution")
        attr_html = f'<footer>— {_esc(attr)}</footer>' if attr else ""
        return f"<blockquote>«{text}»{attr_html}</blockquote>"
    if t == "callout_historical":
        year = _esc(b.get("year")) if b.get("year") else ""
        year_html = f'<span class="year">{year}</span>' if year else ""
        return f"<aside class='callout'>{year_html}{_esc(b.get('text', ''))}</aside>"
    if t == "cover":
        hero  = _esc(b.get("hero_name") or "")
        dates = _esc(b.get("dates") or "")
        return (
            "<section class='cover'>"
            f"<h1>{hero}</h1>"
            + (f"<p class='dates'>{dates}</p>" if dates else "")
            + "</section>"
        )
    if t == "relatives_table":
        rows = [r for r in (b.get("rows") or []) if isinstance(r, dict)]
        if not rows:
            return ""
        head = "<thead><tr><th>Имя</th><th>Кем приходится</th><th>Годы жизни</th><th>Примечания</th></tr></thead>"
        body = "".join(
            "<tr>"
            f"<td>{_esc(r.get('name'))}</td>"
            f"<td>{_esc(r.get('relation'))}</td>"
            f"<td>{_esc(r.get('dates'))}</td>"
            f"<td>{_esc(r.get('notes'))}</td>"
            "</tr>"
            for r in rows
        )
        return f"<table class='relatives'>{head}<tbody>{body}</tbody></table>"
    if t == "awards_table":
        rows = [r for r in (b.get("rows") or []) if isinstance(r, dict)]
        if not rows:
            return ""
        head = "<thead><tr><th>Год</th><th>Название</th><th>Примечание</th></tr></thead>"
        body = "".join(
            "<tr>"
            f"<td>{_esc(r.get('year'))}</td>"
            f"<td>{_esc(r.get('name'))}</td>"
            f"<td>{_esc(r.get('note'))}</td>"
            "</tr>"
            for r in rows
        )
        return f"<table class='awards'>{head}<tbody>{body}</tbody></table>"
    if t == "timeline_visual":
        events = [e for e in (b.get("events") or []) if isinstance(e, dict)]
        if not events:
            return ""
        items = "".join(
            f"<li><span class='year'>{_esc(e.get('year',''))}</span> {_esc(e.get('event') or e.get('text',''))}</li>"
            for e in events
        )
        return f"<ul class='timeline'>{items}</ul>"
    if t == "contributors_list":
        people = b.get("contributors") or []
        if not people:
            return ""
        items = "".join(
            f"<li>{_esc(p.get('name','') if isinstance(p, dict) else p)}</li>"
            for p in people
        )
        return f"<h3>Кто рассказывал</h3><ul class='contributors'>{items}</ul>"
    if t == "photo_album":
        photos = [p for p in (b.get("photos") or []) if isinstance(p, dict)]
        if not photos:
            return ""
        pm = photos_map or {}
        items = []
        for p in photos:
            fn = p.get("file")
            rec = pm.get(fn) if fn else None
            url = rec.get("url") if isinstance(rec, dict) else None
            caption = _esc(p.get("caption") or rec.get("caption", "") if rec else "")
            if url:
                items.append(
                    f"<figure class='photo'><img src='{_esc(url)}'>"
                    + (f"<figcaption>{caption}</figcaption>" if caption else "")
                    + "</figure>"
                )
            else:
                items.append(
                    f"<p class='photo-placeholder'>[фото {_esc(fn)}"
                    + (f" — {caption}" if caption else "")
                    + "]</p>"
                )
        return f"<div class='photo-album'>{''.join(items)}</div>"
    # Unknown — тихо пропускаем, чтобы не ронять весь PDF
    return ""


def _render_chapter(ch: dict, photos_map: dict | None = None) -> str:
    title  = _esc(ch.get("title") or ch.get("id") or "")
    blocks = ch.get("blocks") or []
    body = "\n".join(_render_block(b, photos_map) for b in blocks if isinstance(b, dict))
    return f"<section class='chapter'><h2>{title}</h2>{body}</section>"


HTML_TEMPLATE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  @page {{ size: A5; margin: 20mm 18mm; }}
  body {{
    font-family: 'PT Serif', Georgia, 'Times New Roman', serif;
    font-size: 11pt; line-height: 1.55; color: #1a1a1a;
    margin: 0; padding: 0;
    -webkit-font-smoothing: antialiased;
  }}
  h1 {{ font-size: 22pt; text-align: center; margin: 0.6em 0 0.2em; font-weight: 700; }}
  h2 {{
    font-size: 16pt; margin: 1.4em 0 0.5em; page-break-before: always;
    border-bottom: 1px solid #cabfa8; padding-bottom: 0.25em;
  }}
  .chapter:first-of-type h2 {{ page-break-before: avoid; }}
  h3 {{ font-size: 12pt; margin: 1.1em 0 0.4em; font-weight: 700; }}
  p  {{ margin: 0 0 0.65em; text-align: justify; hyphens: auto; }}
  blockquote {{
    margin: 1em 1.2em; padding: 0.6em 1em;
    border-left: 3px solid #c8a96e; background: #faf6ec;
    font-style: italic; color: #3a2f1e;
  }}
  blockquote footer {{ font-style: normal; font-size: 9pt; color: #6b5d4d; margin-top: 0.4em; }}
  .callout {{
    background: #eef2f7; border-left: 3px solid #5b7a9e;
    padding: 0.55em 1em; margin: 0.9em 0; font-size: 10pt; color: #33445a;
  }}
  .callout .year {{ font-weight: 700; margin-right: 0.4em; color: #33445a; }}
  .cover {{
    page-break-after: always; text-align: center;
    padding-top: 30mm;
  }}
  .cover .dates {{ font-style: italic; color: #6b5d4d; font-size: 12pt; margin-top: 0.5em; text-align: center; }}
  table {{ width: 100%; border-collapse: collapse; margin: 0.8em 0; font-size: 10pt; }}
  table th {{
    text-align: left; font-weight: 700; padding: 0.35em 0.5em;
    border-bottom: 2px solid #cabfa8; color: #6b5d4d; font-size: 9pt;
    text-transform: uppercase; letter-spacing: 0.3px;
  }}
  table td {{ border-bottom: 1px solid #e0d8c5; padding: 0.35em 0.5em; vertical-align: top; }}
  .timeline {{ list-style: none; padding: 0; margin: 0.8em 0; font-size: 10pt; }}
  .timeline li {{ padding: 0.25em 0; border-bottom: 1px dotted #e0d8c5; }}
  .timeline .year {{ font-weight: 700; display: inline-block; min-width: 3em; color: #7a5f2a; }}
  .contributors {{ list-style: none; padding-left: 0; column-count: 2; font-size: 10pt; }}
  .photo-placeholder {{
    text-align: center; color: #999; font-style: italic; font-size: 9pt;
    padding: 1em; border: 1px dashed #ccc; margin: 1em 0;
  }}
  .photo-album {{ margin: 0.8em 0; }}
  .photo-album .photo {{
    margin: 0.6em 0; page-break-inside: avoid; text-align: center;
  }}
  .photo-album .photo img {{
    max-width: 100%; max-height: 120mm; object-fit: contain;
    border-radius: 3pt;
  }}
  .photo-album .photo figcaption {{
    font-size: 9pt; color: #6b5d4d; font-style: italic; margin-top: 0.3em;
  }}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def render_book_to_html(
    book: dict,
    title: str = "Книга",
    photos_map: dict | None = None,
) -> str:
    """
    Рендерит структуру книги в самодостаточный HTML для последующего → PDF.

    photos_map — {filename: {"url": ..., "caption": ...}} для вставки <img src=url>
    в фотоблоках. Без него фотоблоки рендерятся как placeholder.
    """
    if not isinstance(book, dict):
        raise ValueError("book должен быть dict")
    chapters = book.get("chapters") or []
    body = "\n".join(
        _render_chapter(ch, photos_map) for ch in chapters if isinstance(ch, dict)
    )
    return HTML_TEMPLATE.format(title=_esc(title), body=body)
