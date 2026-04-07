# -*- coding: utf-8 -*-
"""Генерация HTML-презентации из Markdown-анализа конкурента."""
import re
from datetime import date
from pathlib import Path
from typing import Optional


def markdown_to_html_body(md: str) -> str:
    """Конвертирует Markdown в HTML (базовый, без внешних зависимостей)."""
    lines = md.split("\n")
    html_parts = []
    in_list = False
    in_table = False
    table_rows = []

    def flush_table():
        nonlocal in_table, table_rows
        if not table_rows:
            return ""
        out = ['<table class="data-table">']
        for i, row in enumerate(table_rows):
            cells = [c.strip() for c in row.strip("|").split("|")]
            tag = "th" if i == 0 else "td"
            out.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
        out.append("</table>")
        in_table = False
        table_rows = []
        return "\n".join(out)

    def inline(text: str) -> str:
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
        text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
        return text

    for line in lines:
        stripped = line.strip()

        # Table row
        if stripped.startswith("|") and stripped.endswith("|"):
            if not in_table:
                if in_list:
                    html_parts.append("</ul>")
                    in_list = False
                in_table = True
                table_rows = []
            # skip separator rows like |---|---|
            if re.match(r"^\|[\s\-:|]+\|$", stripped):
                continue
            table_rows.append(stripped)
            continue
        elif in_table:
            html_parts.append(flush_table())

        if stripped.startswith("### "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f'<h3 class="sub">{inline(stripped[4:])}</h3>')
        elif stripped.startswith("## "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f'<h2 class="sec">{inline(stripped[3:])}</h2>')
        elif stripped.startswith("# "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f'<h1>{inline(stripped[2:])}</h1>')
        elif stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{inline(stripped[2:])}</li>")
        elif re.match(r"^\d+\.\s", stripped):
            if not in_list:
                html_parts.append("<ol>")
                in_list = True
            html_parts.append(f"<li>{inline(re.sub(r'^\d+\.\s', '', stripped))}</li>")
        elif stripped == "":
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append("")
        else:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<p>{inline(stripped)}</p>")

    if in_list:
        html_parts.append("</ul>")
    if in_table:
        html_parts.append(flush_table())

    return "\n".join(html_parts)


def _extract_sections(md: str) -> list[dict]:
    """Разбивает markdown на секции по заголовкам ##."""
    sections = []
    current = None
    for line in md.split("\n"):
        if line.startswith("## "):
            if current:
                sections.append(current)
            current = {"title": line[3:].strip(), "lines": []}
        elif line.startswith("# "):
            pass  # skip top-level title
        elif current is not None:
            current["lines"].append(line)
    if current:
        sections.append(current)
    return sections


def generate_html_report(
    topic: str,
    analysis_md: str,
    screen_count: int = 0,
    output_path: Optional[Path] = None,
) -> Path:
    """Генерирует HTML-презентацию из Markdown-анализа.

    Args:
        topic: Название продукта (StoryWorth, etc.)
        analysis_md: Markdown-текст анализа от GPT-4o
        screen_count: Количество проанализированных скринов
        output_path: Куда сохранить файл. По умолчанию tasks/audience-research/docs/{topic}-report.html
    """
    if output_path is None:
        project_root = Path(__file__).resolve().parent.parent
        output_path = project_root / "tasks" / "audience-research" / "docs" / f"{topic.lower()}-report.html"

    sections = _extract_sections(analysis_md)
    today = date.today().strftime("%d.%m.%Y")

    section_nav = "\n".join(
        f'<li><a href="#sec-{i}">{s["title"]}</a></li>'
        for i, s in enumerate(sections)
    )

    section_blocks = []
    for i, s in enumerate(sections):
        content_md = "\n".join(s["lines"])
        content_html = markdown_to_html_body(content_md)
        section_blocks.append(f"""
      <section id="sec-{i}" class="section {'section-bg' if i % 2 == 1 else ''}">
        <div class="container">
          <div class="part-num">Раздел {i + 1}</div>
          <h2 class="sec">{s["title"]}</h2>
          <div class="content-body">
            {content_html}
          </div>
        </div>
      </section>""")

    sections_html = "\n".join(section_blocks)

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ГЛАВА — Анализ {topic}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400;1,600&family=Manrope:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --cream:#f9f7f2; --paper:#f0ead9; --parchment:#dfd5c2;
    --ink:#181208; --brown:#44311f; --muted:#72614e;
    --gold:#a8823c; --gold-light:#c9a05e; --white:#ffffff;
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Manrope',sans-serif;background:var(--cream);color:var(--ink);font-size:15px;line-height:1.7}}

  nav{{position:sticky;top:0;z-index:100;background:rgba(249,247,242,.95);backdrop-filter:blur(12px);border-bottom:1px solid var(--parchment);padding:0 2.5rem;display:flex;align-items:center;justify-content:space-between;height:54px}}
  .nav-logo{{font-family:'Playfair Display',serif;font-size:1.1rem;font-weight:700;color:var(--ink)}}
  .nav-logo span{{color:var(--gold)}}
  .nav-badge{{background:var(--gold);color:#fff;font-size:.65rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;padding:.25rem .75rem;border-radius:20px}}
  .nav-links{{display:flex;gap:1.5rem;list-style:none;font-size:.75rem;font-weight:600;letter-spacing:.07em;text-transform:uppercase}}
  .nav-links a{{color:var(--muted);text-decoration:none;transition:color .2s}}
  .nav-links a:hover{{color:var(--gold)}}

  .hero{{background:var(--ink);color:var(--cream);padding:6rem 2.5rem 5rem;text-align:center;position:relative;overflow:hidden}}
  .hero::before{{content:'';position:absolute;inset:0;background:radial-gradient(ellipse 70% 50% at 50% -10%,rgba(168,130,60,.22) 0%,transparent 70%)}}
  .hero-label{{font-size:.7rem;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--gold);margin-bottom:.8rem}}
  .hero h1{{font-family:'Playfair Display',serif;font-size:clamp(2.2rem,5vw,3.5rem);font-weight:700;line-height:1.1;margin-bottom:1rem;position:relative}}
  .hero h1 em{{font-style:italic;color:var(--gold-light)}}
  .hero-sub{{font-size:1rem;color:rgba(249,247,242,.6);max-width:580px;margin:0 auto 2.5rem}}
  .hero-stats{{display:flex;justify-content:center;gap:2.5rem;flex-wrap:wrap}}
  .stat{{text-align:center}}
  .stat-num{{font-family:'Playfair Display',serif;font-size:2.2rem;font-weight:700;color:var(--gold-light);line-height:1}}
  .stat-label{{font-size:.72rem;color:rgba(249,247,242,.45);text-transform:uppercase;letter-spacing:.1em;margin-top:.2rem}}

  .container{{max-width:900px;margin:0 auto;padding:4rem 2.5rem}}
  .section{{border-top:1px solid var(--parchment)}}
  .section-bg{{background:var(--paper)}}
  .part-num{{font-size:.65rem;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--gold);margin-bottom:.6rem}}
  h2.sec{{font-family:'Playfair Display',serif;font-size:clamp(1.5rem,3vw,2.2rem);font-weight:700;color:var(--ink);margin-bottom:1.75rem}}
  h3.sub{{font-family:'Playfair Display',serif;font-size:1.1rem;font-weight:600;color:var(--brown);margin-bottom:.6rem;margin-top:1.8rem}}
  h3.sub:first-child{{margin-top:0}}

  .content-body p{{margin-bottom:1rem;color:#2a200f}}
  .content-body ul,.content-body ol{{padding-left:1.5rem;margin-bottom:1rem}}
  .content-body li{{margin-bottom:.4rem}}
  .content-body strong{{font-weight:700;color:var(--ink)}}
  .content-body code{{background:var(--parchment);padding:.1rem .4rem;border-radius:3px;font-size:.9em}}
  .content-body a{{color:var(--gold);text-decoration:underline}}

  .data-table{{width:100%;border-collapse:collapse;margin:1.5rem 0;font-size:.88rem}}
  .data-table th{{background:var(--ink);color:var(--cream);padding:.6rem 1rem;text-align:left;font-weight:600}}
  .data-table td{{padding:.55rem 1rem;border-bottom:1px solid var(--parchment)}}
  .data-table tr:nth-child(even) td{{background:rgba(223,213,194,.25)}}

  footer{{background:var(--ink);color:rgba(249,247,242,.4);text-align:center;padding:2rem;font-size:.8rem}}
  footer strong{{color:var(--gold-light)}}
</style>
</head>
<body>

<nav>
  <div class="nav-logo">ГЛА<span>ВА</span></div>
  <ul class="nav-links">
    {section_nav}
  </ul>
  <span class="nav-badge">Конкурентный анализ</span>
</nav>

<header class="hero">
  <div class="hero-label">Продуктовый анализ</div>
  <h1>Анализ <em>{topic}</em></h1>
  <p class="hero-sub">Mystery shopper исследование — UX, фичи, гипотезы для ГЛАВА</p>
  <div class="hero-stats">
    <div class="stat">
      <div class="stat-num">{screen_count}</div>
      <div class="stat-label">скринов</div>
    </div>
    <div class="stat">
      <div class="stat-num">{len(sections)}</div>
      <div class="stat-label">разделов</div>
    </div>
    <div class="stat">
      <div class="stat-num">{today}</div>
      <div class="stat-label">дата</div>
    </div>
  </div>
</header>

{sections_html}

<footer>
  <p>Сформировано CCO-агентом <strong>ГЛАВА</strong> · {today}</p>
</footer>

</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path

