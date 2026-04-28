# -*- coding: utf-8 -*-
"""
Генерирует brand-book.html для ГЛАВА — встраивает PNG логотипы в base64.
"""
import base64, pathlib

BRAND_DIR = pathlib.Path(r"c:\Users\user\Dropbox\Public\Cursor\GLAVA\tasks\audience-research\brand")

def b64(name):
    p = BRAND_DIR / f"{name}.png"
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()

A = b64("logo_concept_A_serif_gold")
B = b64("logo_concept_B_ornamental_initial")
C = b64("logo_concept_C_modern_minimal")

HTML = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ГЛАВА — Brand Identity</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&family=Manrope:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --cream:     #FAF6EF;
    --paper:     #F3EDE0;
    --parchment: #E8DCC8;
    --gold:      #C9922A;
    --gold-light:#E8B84B;
    --ink:       #1A1410;
    --ink-mid:   #2C2118;
    --brown:     #6B4226;
    --muted:     #8C7B6B;
    --white:     #FFFFFF;
  }}

  body {{
    font-family: 'Manrope', sans-serif;
    background: var(--cream);
    color: var(--ink);
    line-height: 1.6;
  }}

  /* NAV */
  nav {{
    position: sticky; top: 0; z-index: 100;
    background: var(--ink-mid);
    padding: 0 48px;
    display: flex; align-items: center; gap: 32px;
    height: 56px;
  }}
  nav a {{
    color: var(--parchment); text-decoration: none;
    font-size: 13px; font-weight: 500; letter-spacing: .06em;
    opacity: .7; transition: opacity .2s;
  }}
  nav a:hover {{ opacity: 1; }}
  nav .nav-logo {{
    font-family: 'Playfair Display', serif;
    color: var(--gold); font-size: 18px; font-weight: 700;
    margin-right: auto; opacity: 1;
  }}

  /* HERO */
  .hero {{
    background: var(--ink-mid);
    padding: 96px 48px 80px;
    text-align: center;
    position: relative; overflow: hidden;
  }}
  .hero::before {{
    content: '';
    position: absolute; inset: 0;
    background: radial-gradient(ellipse at 50% 120%, rgba(201,146,42,.15) 0%, transparent 70%);
  }}
  .hero-eyebrow {{
    font-size: 11px; letter-spacing: .2em; text-transform: uppercase;
    color: var(--gold); font-weight: 600; margin-bottom: 16px;
  }}
  .hero h1 {{
    font-family: 'Playfair Display', serif;
    font-size: clamp(42px, 6vw, 72px); font-weight: 700;
    color: var(--cream); line-height: 1.1; margin-bottom: 16px;
  }}
  .hero h1 span {{ color: var(--gold); }}
  .hero-sub {{
    font-size: 16px; color: var(--parchment); opacity: .7;
    max-width: 520px; margin: 0 auto;
  }}

  /* SECTIONS */
  section {{
    padding: 80px 48px;
    max-width: 1200px;
    margin: 0 auto;
  }}
  .section-label {{
    font-size: 11px; letter-spacing: .2em; text-transform: uppercase;
    color: var(--gold); font-weight: 600; margin-bottom: 8px;
  }}
  .section-title {{
    font-family: 'Playfair Display', serif;
    font-size: clamp(26px, 3vw, 38px); font-weight: 700;
    color: var(--ink-mid); margin-bottom: 40px;
    border-bottom: 1px solid var(--parchment); padding-bottom: 16px;
  }}
  .divider {{
    border: none; border-top: 1px solid var(--parchment);
    margin: 0;
  }}

  /* LOGO GRID */
  .logo-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 24px;
  }}
  .logo-card {{
    border-radius: 16px; overflow: hidden;
    border: 1px solid var(--parchment);
    background: var(--white);
    transition: transform .2s, box-shadow .2s;
  }}
  .logo-card:hover {{
    transform: translateY(-4px);
    box-shadow: 0 20px 48px rgba(26,20,16,.12);
  }}
  .logo-card.winner {{
    border-color: var(--gold);
    box-shadow: 0 0 0 2px var(--gold), 0 16px 40px rgba(201,146,42,.15);
  }}
  .logo-preview {{
    display: flex; align-items: center; justify-content: center;
    padding: 40px 24px;
    min-height: 240px;
    background: var(--white);
  }}
  .logo-preview img {{
    max-width: 280px; max-height: 200px;
    object-fit: contain;
  }}
  .logo-preview.dark {{ background: var(--ink-mid); }}
  .logo-preview.cream {{ background: var(--cream); }}
  .logo-info {{
    padding: 20px 24px 24px;
    background: var(--paper);
    border-top: 1px solid var(--parchment);
  }}
  .logo-badge {{
    display: inline-block;
    font-size: 10px; letter-spacing: .12em; text-transform: uppercase;
    padding: 3px 10px; border-radius: 20px;
    font-weight: 600; margin-bottom: 10px;
  }}
  .badge-winner {{ background: var(--gold); color: var(--white); }}
  .badge-alt {{ background: var(--parchment); color: var(--brown); }}
  .logo-info h3 {{
    font-family: 'Playfair Display', serif;
    font-size: 18px; font-weight: 700;
    color: var(--ink-mid); margin-bottom: 8px;
  }}
  .logo-info p {{
    font-size: 13px; color: var(--muted); line-height: 1.6;
  }}
  .logo-tags {{
    margin-top: 12px; display: flex; flex-wrap: wrap; gap: 6px;
  }}
  .tag {{
    font-size: 11px; padding: 2px 8px; border-radius: 4px;
    background: var(--parchment); color: var(--brown);
  }}

  /* WINNER SHOWCASE */
  .winner-showcase {{
    background: var(--ink-mid);
    border-radius: 24px;
    padding: 64px;
    display: grid; grid-template-columns: 1fr 1fr; gap: 48px;
    align-items: center;
  }}
  .winner-showcase img {{
    width: 100%; max-width: 360px; margin: auto;
    display: block; border-radius: 12px;
  }}
  .winner-info .eyebrow {{
    font-size: 11px; letter-spacing: .2em; text-transform: uppercase;
    color: var(--gold); font-weight: 600; margin-bottom: 12px;
  }}
  .winner-info h2 {{
    font-family: 'Playfair Display', serif;
    font-size: 32px; color: var(--cream);
    font-weight: 700; margin-bottom: 20px; line-height: 1.2;
  }}
  .winner-info p {{
    font-size: 15px; color: var(--parchment); opacity: .8;
    margin-bottom: 12px; line-height: 1.7;
  }}

  /* USAGE GRID */
  .usage-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
  }}
  .usage-card {{
    border-radius: 12px; overflow: hidden;
    border: 1px solid var(--parchment);
  }}
  .usage-preview {{
    height: 120px;
    display: flex; align-items: center; justify-content: center;
    padding: 16px;
  }}
  .usage-preview img {{ max-width: 100%; max-height: 88px; object-fit: contain; }}
  .usage-label {{
    padding: 10px 14px;
    background: var(--paper);
    border-top: 1px solid var(--parchment);
    font-size: 12px; font-weight: 600; color: var(--brown);
    text-align: center; text-transform: uppercase; letter-spacing: .08em;
  }}

  /* FAVICON MOCKUP */
  .favicon-row {{
    display: flex; gap: 16px; flex-wrap: wrap; align-items: flex-end;
  }}
  .fav-box {{
    text-align: center;
  }}
  .fav-box .fav-img {{
    display: flex; align-items: center; justify-content: center;
    background: var(--cream);
    border: 1px solid var(--parchment);
    border-radius: 8px;
    margin: 0 auto 8px;
    overflow: hidden;
  }}
  .fav-box .fav-img img {{ object-fit: contain; }}
  .fav-box .fav-label {{
    font-size: 11px; color: var(--muted);
  }}

  /* COLORS */
  .color-grid {{
    display: flex; gap: 16px; flex-wrap: wrap;
  }}
  .color-swatch {{
    flex: 1; min-width: 120px; max-width: 160px;
    border-radius: 12px; overflow: hidden;
    border: 1px solid rgba(0,0,0,.06);
    box-shadow: 0 2px 8px rgba(0,0,0,.06);
  }}
  .swatch-color {{
    height: 100px;
  }}
  .swatch-info {{
    padding: 12px 14px;
    background: var(--white);
  }}
  .swatch-name {{
    font-weight: 600; font-size: 13px; color: var(--ink-mid); margin-bottom: 2px;
  }}
  .swatch-hex {{
    font-size: 11px; color: var(--muted); font-family: monospace;
  }}
  .swatch-role {{
    font-size: 11px; color: var(--muted); margin-top: 4px;
  }}

  /* TYPOGRAPHY */
  .type-grid {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 32px;
  }}
  .type-card {{
    padding: 32px;
    background: var(--paper);
    border-radius: 16px;
    border: 1px solid var(--parchment);
  }}
  .type-card .type-specimen {{
    font-size: 42px; margin-bottom: 16px; line-height: 1.1;
    color: var(--ink-mid);
  }}
  .type-card .type-name {{
    font-weight: 600; font-size: 14px; color: var(--gold);
    text-transform: uppercase; letter-spacing: .1em; margin-bottom: 4px;
  }}
  .type-card .type-desc {{
    font-size: 13px; color: var(--muted);
  }}
  .type-card .type-sample {{
    margin-top: 16px; padding-top: 16px;
    border-top: 1px solid var(--parchment);
    font-size: 13px; color: var(--ink-mid); line-height: 1.7;
  }}

  /* BRAND VOICE */
  .voice-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
  }}
  .voice-card {{
    padding: 24px;
    border-radius: 12px;
    border: 1px solid var(--parchment);
  }}
  .voice-card.yes {{ border-left: 3px solid #5B8E5B; background: #F3F8F3; }}
  .voice-card.no  {{ border-left: 3px solid #C25050; background: #FDF4F4; }}
  .voice-card h4 {{
    font-size: 11px; letter-spacing: .15em; text-transform: uppercase;
    font-weight: 600; margin-bottom: 12px;
  }}
  .voice-card.yes h4 {{ color: #5B8E5B; }}
  .voice-card.no h4  {{ color: #C25050; }}
  .voice-card ul {{
    list-style: none; font-size: 13px; color: var(--ink-mid);
  }}
  .voice-card ul li {{ margin-bottom: 6px; padding-left: 16px; position: relative; }}
  .voice-card.yes ul li::before {{ content: '✓'; position: absolute; left: 0; color: #5B8E5B; }}
  .voice-card.no  ul li::before {{ content: '✗'; position: absolute; left: 0; color: #C25050; }}

  /* APPLICATIONS */
  .app-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 24px;
  }}
  .app-mockup {{
    border-radius: 16px; overflow: hidden;
    border: 1px solid var(--parchment);
  }}
  .app-header {{
    padding: 20px 24px 16px;
    display: flex; align-items: center; gap: 12px;
  }}
  .app-icon {{
    width: 40px; height: 40px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-family: 'Playfair Display', serif;
    font-size: 18px; font-weight: 700;
    color: var(--white);
  }}
  .app-icon.gold-bg  {{ background: var(--gold); }}
  .app-icon.ink-bg   {{ background: var(--ink-mid); }}
  .app-icon.cream-bg {{ background: var(--paper); color: var(--ink-mid); }}
  .app-title {{
    font-weight: 600; font-size: 14px; color: var(--ink-mid);
  }}
  .app-sub {{
    font-size: 12px; color: var(--muted);
  }}
  .app-body {{
    padding: 0 24px 24px;
    font-size: 13px; color: var(--muted); line-height: 1.6;
  }}

  /* FOOTER */
  footer {{
    background: var(--ink-mid);
    padding: 48px;
    text-align: center;
    color: var(--parchment);
    opacity: .6;
    font-size: 13px;
  }}

  @media (max-width: 768px) {{
    section {{ padding: 48px 24px; }}
    .winner-showcase {{ grid-template-columns: 1fr; padding: 32px; }}
    .type-grid {{ grid-template-columns: 1fr; }}
    nav {{ padding: 0 24px; gap: 20px; }}
  }}
</style>
</head>
<body>

<nav>
  <span class="nav-logo">ГЛАВА</span>
  <a href="#concepts">Концепты</a>
  <a href="#winner">Финалист</a>
  <a href="#usage">Применение</a>
  <a href="#colors">Цвета</a>
  <a href="#typography">Типографика</a>
  <a href="#voice">Тон</a>
</nav>

<!-- HERO -->
<div class="hero">
  <div class="hero-eyebrow">Brand Identity · glava.family</div>
  <h1>Фирменный стиль<br><span>ГЛАВА</span></h1>
  <p class="hero-sub">Три концепта логотипа, палитра, типографика и принципы бренда — тёплого, премиального, семейного</p>
</div>

<!-- CONCEPTS -->
<section id="concepts">
  <div class="section-label">Шаг 1 · Концепты</div>
  <div class="section-title">Три направления логотипа</div>

  <div class="logo-grid">

    <!-- CONCEPT C — winner -->
    <div class="logo-card winner">
      <div class="logo-preview cream">
        <img src="{C}" alt="Концепт C — ГЛАВА кириллица">
      </div>
      <div class="logo-info">
        <span class="logo-badge badge-winner">★ Рекомендованный</span>
        <h3>Концепт В — Кириллический минимализм</h3>
        <p>ГЛАВА в кириллице. Буква Г стилизована под перевёрнутую страницу — прямая отсылка к книге. Тёмный чернильный цвет на кремовом фоне, горизонтальная черта — лаконичный акцент. Работает везде: web, app icon, печать, Telegram.</p>
        <div class="logo-tags">
          <span class="tag">Кириллица</span>
          <span class="tag">Минимализм</span>
          <span class="tag">Книга/страница</span>
          <span class="tag">Versatile</span>
        </div>
      </div>
    </div>

    <!-- CONCEPT B -->
    <div class="logo-card">
      <div class="logo-preview cream">
        <img src="{B}" alt="Концепт B — Орнаментальный медальон">
      </div>
      <div class="logo-info">
        <span class="logo-badge badge-alt">Альтернатива А</span>
        <h3>Концепт А — Heritage медальон</h3>
        <p>Орнаментальный круглый медальон с монограммой Г, обрамлённой золотым лавровым венком. Кремовый фон, золото и коричневый — классическое сочетание. Идеален для бумажных носителей: сертификат, обложка книги, благодарственная открытка.</p>
        <div class="logo-tags">
          <span class="tag">Heritage</span>
          <span class="tag">Орнамент</span>
          <span class="tag">Печать</span>
          <span class="tag">Медальон</span>
        </div>
      </div>
    </div>

    <!-- CONCEPT A -->
    <div class="logo-card">
      <div class="logo-preview" style="background:#fff;">
        <img src="{A}" alt="Концепт A — Gold serif wordmark">
      </div>
      <div class="logo-info">
        <span class="logo-badge badge-alt">Альтернатива Б</span>
        <h3>Концепт Б — Gold serif wordmark</h3>
        <p>Wordmark GLAVA в золотом цвете с утончённым serif-шрифтом. Классический, банковский стиль — считывается как премиум. Пригоден для англоязычных рынков или как суббренд. Доменная подпись glava.family в нейтральном сером.</p>
        <div class="logo-tags">
          <span class="tag">Gold</span>
          <span class="tag">Serif</span>
          <span class="tag">Premium</span>
          <span class="tag">Wordmark</span>
        </div>
      </div>
    </div>

  </div>
</section>

<hr class="divider">

<!-- WINNER SHOWCASE -->
<section id="winner">
  <div class="section-label">Шаг 2 · Финалист</div>
  <div class="section-title">Рекомендованный логотип</div>

  <div class="winner-showcase">
    <img src="{C}" alt="ГЛАВА — финальный логотип">
    <div class="winner-info">
      <div class="eyebrow">Обоснование выбора</div>
      <h2>Почему именно<br>этот концепт</h2>
      <p><strong style="color:var(--gold)">Кириллица</strong> — главная просьба заказчика. Логотип читается как «ГЛАВА» по-русски, без переключения алфавита.</p>
      <p><strong style="color:var(--gold)">Буква Г</strong> со скруглённым верхним углом — ненавязчивая отсылка к перевёрнутой странице или открытой книге. Смысловой символ встроен в буквенное начертание.</p>
      <p><strong style="color:var(--gold)">Горизонтальная черта</strong> под словом добавляет стабильность и создаёт композиционный «постамент» — логотип ощущается как подпись, как печать.</p>
      <p><strong style="color:var(--gold)">Тёмный чернильный + кремовый</strong> — цвета старой бумаги, чернил, книжного текста. Тёплые, не холодные. Не стартап, а семейная ценность.</p>
    </div>
  </div>
</section>

<hr class="divider">

<!-- USAGE VARIANTS -->
<section id="usage">
  <div class="section-label">Шаг 3 · Применение</div>
  <div class="section-title">Варианты использования</div>

  <div class="usage-grid">
    <div class="usage-card">
      <div class="usage-preview" style="background:#FAF6EF;">
        <img src="{C}" alt="На кремовом">
      </div>
      <div class="usage-label">Основной · кремовый</div>
    </div>
    <div class="usage-card">
      <div class="usage-preview" style="background:#fff;">
        <img src="{C}" alt="На белом">
      </div>
      <div class="usage-label">На белом</div>
    </div>
    <div class="usage-card">
      <div class="usage-preview" style="background:#2C2118;">
        <img src="{C}" alt="На тёмном">
      </div>
      <div class="usage-label">Инвертированный</div>
    </div>
    <div class="usage-card">
      <div class="usage-preview" style="background:#E8DCC8;">
        <img src="{C}" alt="На пергаменте">
      </div>
      <div class="usage-label">На пергаменте</div>
    </div>
    <div class="usage-card">
      <div class="usage-preview" style="background:#C9922A;">
        <img src="{C}" alt="На золотом">
      </div>
      <div class="usage-label">На золотом</div>
    </div>
    <div class="usage-card">
      <div class="usage-preview" style="background:#FAF6EF;">
        <img src="{B}" alt="Медальон — бумажный носитель">
      </div>
      <div class="usage-label">Медальон · бумага</div>
    </div>
  </div>

  <!-- Favicon sizes -->
  <h3 style="margin-top:48px; margin-bottom:24px; font-family:'Playfair Display',serif; font-size:20px; color:var(--ink-mid);">Favicon / App Icon</h3>
  <div class="favicon-row">
    <div class="fav-box">
      <div class="fav-img" style="width:180px;height:180px;">
        <img src="{C}" style="width:180px;height:180px;" alt="">
      </div>
      <div class="fav-label">512 × 512 · App Store</div>
    </div>
    <div class="fav-box">
      <div class="fav-img" style="width:96px;height:96px;">
        <img src="{C}" style="width:96px;height:96px;" alt="">
      </div>
      <div class="fav-label">96 × 96</div>
    </div>
    <div class="fav-box">
      <div class="fav-img" style="width:48px;height:48px;">
        <img src="{C}" style="width:48px;height:48px;" alt="">
      </div>
      <div class="fav-label">48 × 48</div>
    </div>
    <div class="fav-box">
      <div class="fav-img" style="width:32px;height:32px; border-radius:4px;">
        <img src="{C}" style="width:32px;height:32px;" alt="">
      </div>
      <div class="fav-label">32 × 32</div>
    </div>
    <div class="fav-box">
      <div class="fav-img" style="width:16px;height:16px; border-radius:2px;">
        <img src="{C}" style="width:16px;height:16px;" alt="">
      </div>
      <div class="fav-label">16 × 16</div>
    </div>
    <div class="fav-box" style="margin-left:24px;">
      <div class="fav-img" style="width:180px;height:180px; background:#2C2118; border-radius:40px;">
        <img src="{C}" style="width:140px;height:140px;" alt="">
      </div>
      <div class="fav-label">Telegram-аватар</div>
    </div>
  </div>
</section>

<hr class="divider">

<!-- COLORS -->
<section id="colors">
  <div class="section-label">Шаг 4 · Палитра</div>
  <div class="section-title">Фирменные цвета</div>

  <div class="color-grid">
    <div class="color-swatch">
      <div class="swatch-color" style="background:#1A1410;"></div>
      <div class="swatch-info">
        <div class="swatch-name">Ink</div>
        <div class="swatch-hex">#1A1410</div>
        <div class="swatch-role">Основной текст, логотип</div>
      </div>
    </div>
    <div class="color-swatch">
      <div class="swatch-color" style="background:#2C2118;"></div>
      <div class="swatch-info">
        <div class="swatch-name">Ink Mid</div>
        <div class="swatch-hex">#2C2118</div>
        <div class="swatch-role">Тёмные блоки, nav</div>
      </div>
    </div>
    <div class="color-swatch">
      <div class="swatch-color" style="background:#C9922A;"></div>
      <div class="swatch-info">
        <div class="swatch-name">Gold</div>
        <div class="swatch-hex">#C9922A</div>
        <div class="swatch-role">Акцент, CTA, логотип A</div>
      </div>
    </div>
    <div class="color-swatch">
      <div class="swatch-color" style="background:#E8B84B;"></div>
      <div class="swatch-info">
        <div class="swatch-name">Gold Light</div>
        <div class="swatch-hex">#E8B84B</div>
        <div class="swatch-role">Hover, иконки, орнамент</div>
      </div>
    </div>
    <div class="color-swatch">
      <div class="swatch-color" style="background:#FAF6EF; border: 1px solid #E8DCC8;"></div>
      <div class="swatch-info">
        <div class="swatch-name">Cream</div>
        <div class="swatch-hex">#FAF6EF</div>
        <div class="swatch-role">Основной фон</div>
      </div>
    </div>
    <div class="color-swatch">
      <div class="swatch-color" style="background:#F3EDE0;"></div>
      <div class="swatch-info">
        <div class="swatch-name">Paper</div>
        <div class="swatch-hex">#F3EDE0</div>
        <div class="swatch-role">Карточки, секции</div>
      </div>
    </div>
    <div class="color-swatch">
      <div class="swatch-color" style="background:#E8DCC8;"></div>
      <div class="swatch-info">
        <div class="swatch-name">Parchment</div>
        <div class="swatch-hex">#E8DCC8</div>
        <div class="swatch-role">Разделители, бордеры</div>
      </div>
    </div>
    <div class="color-swatch">
      <div class="swatch-color" style="background:#8C7B6B;"></div>
      <div class="swatch-info">
        <div class="swatch-name">Muted</div>
        <div class="swatch-hex">#8C7B6B</div>
        <div class="swatch-role">Вторичный текст</div>
      </div>
    </div>
  </div>
</section>

<hr class="divider">

<!-- TYPOGRAPHY -->
<section id="typography">
  <div class="section-label">Шаг 5 · Типографика</div>
  <div class="section-title">Шрифтовая пара</div>

  <div class="type-grid">
    <div class="type-card">
      <div class="type-specimen" style="font-family:'Playfair Display',serif; font-style:italic;">Семья</div>
      <div class="type-name">Playfair Display</div>
      <div class="type-desc">Заголовки, цитаты, логотип · Serif · Google Fonts</div>
      <div class="type-sample" style="font-family:'Playfair Display',serif;">
        «Каждая семья — это отдельная глава<br>в большой книге человечества.»<br><br>
        <span style="font-weight:700;">Bold 700</span> · <span style="font-style:italic;">Italic 400</span> · Regular 400
      </div>
    </div>
    <div class="type-card">
      <div class="type-specimen" style="font-family:'Manrope',sans-serif; font-weight:300;">История</div>
      <div class="type-name">Manrope</div>
      <div class="type-desc">Интерфейс, body, кнопки · Sans-serif · Google Fonts</div>
      <div class="type-sample">
        Сохраните историю своей семьи навсегда.<br>30 минут записи — и книга готова.<br><br>
        <span style="font-weight:600;">SemiBold 600</span> · <span style="font-weight:400;">Regular 400</span> · <span style="font-weight:300;">Light 300</span>
      </div>
    </div>
  </div>

  <div style="margin-top:32px; padding:32px; background:var(--paper); border-radius:16px; border:1px solid var(--parchment);">
    <div style="font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:var(--gold);font-weight:600;margin-bottom:16px;">Иерархия текста</div>
    <div style="font-family:'Playfair Display',serif;font-size:36px;font-weight:700;color:var(--ink-mid);margin-bottom:8px;">H1 — Главный заголовок</div>
    <div style="font-family:'Playfair Display',serif;font-size:24px;font-weight:600;color:var(--ink-mid);margin-bottom:8px;">H2 — Заголовок раздела</div>
    <div style="font-family:'Playfair Display',serif;font-size:18px;font-style:italic;color:var(--brown);margin-bottom:16px;">Цитата или подзаголовок</div>
    <div style="font-size:15px;color:var(--ink-mid);line-height:1.7;margin-bottom:8px;">Основной текст — Manrope 15px, line-height 1.7. Тёплый тон, без корпоративного. Пишем как живой человек, а не как маркетолог.</div>
    <div style="font-size:13px;color:var(--muted);">Вторичный текст, подписи, мета — Manrope 13px, color: #8C7B6B</div>
  </div>
</section>

<hr class="divider">

<!-- BRAND VOICE -->
<section id="voice">
  <div class="section-label">Шаг 6 · Голос бренда</div>
  <div class="section-title">Тон и голос</div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:40px;">
    <div class="voice-card yes">
      <h4>Говорим</h4>
      <ul>
        <li>Тепло и по-семейному</li>
        <li>С уважением к памяти</li>
        <li>Просто о сложном процессе</li>
        <li>«Книга о бабушке», «история семьи»</li>
        <li>«Литературная обработка»</li>
        <li>«30 минут записи — достаточно»</li>
        <li>«Мы задаём вопросы»</li>
      </ul>
    </div>
    <div class="voice-card no">
      <h4>Избегаем</h4>
      <ul>
        <li>«AI-генерация», «нейросеть»</li>
        <li>Технических терминов</li>
        <li>Корпоративного тона</li>
        <li>Срочности и давления («успей»)</li>
        <li>«Биография» (слишком официально)</li>
        <li>«Транскрипт», «расшифровка»</li>
        <li>Излишней скромности</li>
      </ul>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;">
    <div style="padding:24px;background:var(--paper);border-radius:12px;border:1px solid var(--parchment);">
      <div style="font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:var(--gold);font-weight:600;margin-bottom:12px;">Теплота</div>
      <div style="font-size:13px;color:var(--ink-mid);line-height:1.7;">Не услуга — забота. Не продукт — подарок близкому человеку.</div>
    </div>
    <div style="padding:24px;background:var(--paper);border-radius:12px;border:1px solid var(--parchment);">
      <div style="font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:var(--gold);font-weight:600;margin-bottom:12px;">Простота</div>
      <div style="font-size:13px;color:var(--ink-mid);line-height:1.7;">Вам не нужно ничего уметь. Просто говорите — мы сделаем всё остальное.</div>
    </div>
    <div style="padding:24px;background:var(--paper);border-radius:12px;border:1px solid var(--parchment);">
      <div style="font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:var(--gold);font-weight:600;margin-bottom:12px;">Премиальность</div>
      <div style="font-size:13px;color:var(--ink-mid);line-height:1.7;">Настоящая книга с обложкой, именем, фотографиями. Не файл — артефакт.</div>
    </div>
    <div style="padding:24px;background:var(--paper);border-radius:12px;border:1px solid var(--parchment);">
      <div style="font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:var(--gold);font-weight:600;margin-bottom:12px;">Доверие</div>
      <div style="font-size:13px;color:var(--ink-mid);line-height:1.7;">Всё конфиденциально. Ваши истории принадлежат только вам и вашей семье.</div>
    </div>
  </div>
</section>

<hr class="divider">

<!-- APPLICATIONS -->
<section>
  <div class="section-label">Шаг 7 · Носители</div>
  <div class="section-title">Применение в интерфейсах</div>

  <div class="app-grid">

    <!-- Telegram Bot -->
    <div class="app-mockup" style="background:var(--white);">
      <div class="app-header" style="background:#229ED9;color:#fff;gap:12px;">
        <div class="app-icon" style="background:rgba(255,255,255,.2);color:#fff;font-size:16px;">Г</div>
        <div>
          <div class="app-title" style="color:#fff;">ГЛАВА</div>
          <div class="app-sub" style="color:rgba(255,255,255,.7);">@glava_family_bot</div>
        </div>
      </div>
      <div style="padding:16px;display:flex;flex-direction:column;gap:10px;">
        <div style="background:#E8F4FD;border-radius:12px 12px 12px 4px;padding:12px 14px;font-size:13px;max-width:85%;">
          Привет! Я помогу сохранить историю вашей семьи в виде книги. Расскажите, о ком вы хотите написать?
        </div>
        <div style="background:var(--gold);color:#fff;border-radius:12px 12px 4px 12px;padding:12px 14px;font-size:13px;max-width:85%;align-self:flex-end;">
          О моей бабушке, ей 82 года
        </div>
      </div>
      <div class="app-body">Telegram Bot · основной канал продукта</div>
    </div>

    <!-- Website header -->
    <div class="app-mockup" style="background:var(--cream);">
      <div class="app-header" style="background:var(--ink-mid);border-bottom:none;">
        <div class="app-icon ink-bg" style="background:none;padding:0;">
          <img src="{C}" style="width:36px;height:36px;object-fit:contain;" alt="">
        </div>
        <div>
          <div class="app-title" style="font-family:'Playfair Display',serif;color:var(--cream);font-size:16px;">ГЛАВА</div>
          <div class="app-sub" style="color:var(--parchment);opacity:.6;">glava.family</div>
        </div>
      </div>
      <div style="padding:24px;">
        <div style="font-family:'Playfair Display',serif;font-size:22px;font-weight:700;color:var(--ink-mid);margin-bottom:8px;line-height:1.3;">Семейная книга за один разговор</div>
        <div style="font-size:13px;color:var(--muted);margin-bottom:16px;">30 минут голоса — и история сохранена навсегда</div>
        <div style="display:inline-block;background:var(--gold);color:#fff;padding:10px 20px;border-radius:8px;font-size:13px;font-weight:600;">Начать →</div>
      </div>
      <div class="app-body">Лендинг · glava.family</div>
    </div>

    <!-- Book cover -->
    <div class="app-mockup" style="background:var(--paper);">
      <div style="padding:24px;display:flex;justify-content:center;">
        <div style="width:160px;background:var(--ink-mid);border-radius:4px 12px 12px 4px;padding:20px 16px;box-shadow:4px 4px 16px rgba(0,0,0,.3);">
          <div style="text-align:center;margin-bottom:16px;">
            <img src="{B}" style="width:80px;height:80px;object-fit:contain;border-radius:50%;background:var(--cream);padding:4px;" alt="">
          </div>
          <div style="font-family:'Playfair Display',serif;font-size:11px;font-style:italic;color:var(--gold);text-align:center;margin-bottom:4px;">Воспоминания</div>
          <div style="font-family:'Playfair Display',serif;font-size:15px;font-weight:700;color:var(--cream);text-align:center;line-height:1.2;">Анна<br>Петровна</div>
          <div style="border-top:1px solid rgba(201,146,42,.3);margin:12px 0;"></div>
          <div style="font-family:'Playfair Display',serif;font-size:8px;color:var(--gold);text-align:center;letter-spacing:.1em;">ГЛАВА · glava.family</div>
        </div>
      </div>
      <div class="app-body">Обложка книги · медальон как декор</div>
    </div>

  </div>
</section>

<footer>
  ГЛАВА · Brand Identity · glava.family · 2026<br>
  Логотипы сгенерированы через Replicate / google/nano-banana-2
</footer>

</body>
</html>
"""

out = BRAND_DIR / "brand-book.html"
out.write_text(HTML, encoding="utf-8")
print(f"Saved: {out}")
print(f"Size: {len(HTML)//1024} KB")
