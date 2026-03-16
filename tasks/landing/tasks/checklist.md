# Чек-лист задачи: Лендинг glava.family

> Детальный список задач по фазам. Общий статус — в `status.md`.

---

## Фаза 1 — Разработка MVP ✅

### HTML-структура
- [x] `<!DOCTYPE html>`, meta charset, viewport
- [x] Подключение Google Fonts (Playfair Display + Manrope)
- [x] CSS-переменные (`:root`) — палитра, типографика
- [x] Reset CSS
- [x] Базовая сетка (`.container`, `.section`)

### Блоки
- [x] `<nav>` — логотип + бургер + drawer + overlay
- [x] `<section.hero>` — eyebrow, h1, tagline, desc, CTA, trust-markers, book-wrap
- [x] `<section.values-section>` — 3 карточки с иконками
- [x] `<section.how-section>` — 3 шага с иконками и connecting line
- [x] `<section.sample-section>` — book-мокап + список качества + CTA
- [x] `<section.reviews-section>` — carousel container
- [x] `<section.faq-section>` — accordion container
- [x] `<section.final-section>` — dark block CTA
- [x] `<footer>` — grid, socials, nav, contacts, legal

### JavaScript
- [x] Scroll listener → `.scrolled` класс на nav
- [x] Burger/drawer: `toggleDrawer()`, overlay click, data-drawer-close
- [x] Reviews carousel: render из массива `REVIEWS`, goTo(), resetAuto(), touch swipe
- [x] FAQ accordion: render из массива `FAQ`, toggle open/close
- [x] Данные вынесены в JS-константы `REVIEWS` и `FAQ` (легко расширять)

### Адаптивность
- [x] Breakpoint 900px — одна колонка, hero stack
- [x] Breakpoint 480px — кнопки полная ширина, уменьшение padding

---

## Фаза 2 — Дизайн-апгрейд ✅

### Layout и масштаб
- [x] Container: 1100px → 1280px
- [x] Desktop-xl: 1440px → container 1360px, section padding 7.5rem
- [x] Section padding: 4rem → 6rem
- [x] `html { font-size: 17px; }`

### Типографика
- [x] `.section-title` clamp(2rem, 3.8vw, 3rem)
- [x] `.section-sub` 1.08rem, line-height 1.8
- [x] `.hero-title` clamp(4.5rem, 9.5vw, 7.5rem)
- [x] `.hero-tagline` clamp(1.15rem, 2.2vw, 1.5rem)
- [x] `.hero-desc` 1.05rem, line-height 1.82
- [x] `.review-text` 1.12rem, line-height 1.88
- [x] `.faq-q` 1.05rem, `.faq-a-inner` 1.02rem

### Компоненты
- [x] Value cards: padding 2.5rem, border parchment, hover shadow
- [x] Step circle: 64px, box-shadow
- [x] Sample book: max-width 360px, richer shadow
- [x] Sample badge: 82px
- [x] Reviews outer: max-width 920px
- [x] Review card: padding 3.25rem 3.5rem
- [x] Review quote mark: 8rem
- [x] FAQ list: max-width 820px
- [x] FAQ open item: box-shadow + border-color gold
- [x] Final title: clamp(1.9rem, 4.5vw, 3.2rem)
- [x] Final ornament decoration

### Цвета (обогащены)
- [x] `--gold: #a8823c` (насыщеннее)
- [x] `--ink: #181208` (темнее)
- [x] `--paper: #f0ead9` (богаче)

---

## Фаза 3 — UX-апгрейд ✅

### Навигация
- [x] `.nav-links` — desktop nav links (display: flex при ≥1025px)
- [x] `.nav-cta` — кнопка «Начать» в шапке (display: flex при ≥1025px)
- [x] `.nav-burger` — display: none при ≥1025px
- [x] `.nav-right` — контейнер для cta + burger

### Hero
- [x] Новый слоган: «Запишите историю близкого — пока она ещё звучит»
- [x] Desc реструктурирован: продукт → формат → результат (конкретно)
- [x] Цена вынесена в отдельный `.hero-price-line`
- [x] Primary CTA: «Начать свою главу»
- [x] Secondary CTA: «Посмотреть пример» (anchor #sample)
- [x] Trust-маркеры: 3 пункта с gold dot
- [x] Book-заглушка удалена из hero (hero стал typographic)

### Values
- [x] Добавлен section-eyebrow «Почему это важно»
- [x] Заголовок: «Не сухая справка — живая история»
- [x] Подзаголовок с целевой аудиторией
- [x] Описания карточек: 2–3 предложения, отвечают «почему это важно для меня»

### Steps
- [x] Заголовок: «Всё проще, чем кажется»
- [x] Подзаголовок: акцент на простоту процесса
- [x] Описания шагов: конкретнее и подробнее
- [x] Reassurance note: «Можно делать несколько разговоров в разное время»

### Sample
- [x] Заголовок: «Биография, а не расшифровка»
- [x] Описание блока: акцент на качество работы редактора
- [x] 4 пункта качества: обновлены формулировки
- [x] Добавлена вторая кнопка «Начать свою главу»

### Mid-CTA
- [x] Новый блок `.mid-cta-strip` между reviews и FAQ
- [x] Тёмный фон (var(--ink))
- [x] Эмоциональная реплика + кнопка btn-white

### FAQ
- [x] Порядок: результат → цена → срок → процесс → формат → конфиденциальность
- [x] Вопросы переформулированы (конкретнее, с «ли» и «и нет ли»)
- [x] Заголовок: «Частые вопросы»

### Final CTA
- [x] `.final-what-get` — 3 check-пункта перед кнопкой
- [x] Подпись изменена: «Напишите «Хочу главу»»

---

## Фаза 4 — Ассеты ⏳

- [ ] Лого (SVG или PNG) → `landing/assets/logo.svg`
- [ ] Hero-фото или обложка книги → `landing/assets/hero.jpg`
- [ ] PDF-пример → `landing/sample.pdf` или URL на S3
- [ ] Иконки соцсетей → заменить текстовые TG/VK/ДЗ/YT
- [ ] Проверить и обновить все ссылки

---

## Фаза 5 — Деплой ⏳

- [ ] Создать `deploy/nginx-glava.conf` (шаблон в plan.md)
- [ ] Согласовать с Агентом А путь на VPS
- [ ] rsync или git pull → `/opt/glava/landing/`
- [ ] `systemctl reload nginx`
- [ ] certbot для HTTPS
- [ ] Проверить: `curl -I https://glava.family/`
- [ ] PageSpeed Insights проверка
- [ ] Google Search Console — добавить сайт
