# Лендинг glava.family — План работ

## Цель задачи

Создать продающий лендинг для сервиса «Глава» на домене `glava.family`.

**Целевое действие:** переход пользователя в Telegram-бот `@glava_voice_bot` и оформление заказа.

**Целевая аудитория:** дети и внуки, которые хотят сохранить историю старшего поколения; люди 35–60 лет, задумывающиеся о семейной памяти.

---

## Фазы работы

### Фаза 1 — Разработка MVP ✅ (15.03.2026)

Реализация по ТЗ заказчика (файл `Лендинг для Главы.docx`).

**Задачи:**
- [x] Hero: заголовок, слоган, описание, CTA, book-заглушка
- [x] Блоки ценностей (3 карточки)
- [x] «Как это работает» (3 шага с иконками)
- [x] Sample-блок (превью книги + кнопка скачать)
- [x] Карусель отзывов (infinite, random start, swipe, dots)
- [x] FAQ accordion (6 вопросов)
- [x] Final CTA (тёмный блок)
- [x] Footer (контакты, соцсети, навигация, юридика)
- [x] Drawer-меню (бургер → slide-in справа)
- [x] Sticky nav с blur при скролле
- [x] Мобильная адаптация (480px, 900px)

### Фаза 2 — Дизайн-апгрейд ✅ (15.03.2026)

Усиление визуального масштаба, типографики и контраста.

**Задачи:**
- [x] Container 1100px → 1280px; breakpoint 1440px → 1360px
- [x] Базовый font-size 16px → 17px
- [x] Усиление всей типографики (section-title, hero-desc, value-desc, review-text и др.)
- [x] Увеличение вертикального ритма секций (4rem → 6rem)
- [x] Hero: trust-маркеры, усиление book-visual (цвета, тени, декор)
- [x] Values: larger cards, border, hover shadow
- [x] Steps: larger circles, reassurance note
- [x] Sample: max-width book 360px, badge 82px, stronger shadow
- [x] Reviews: max-width 920px, larger card padding, quote mark 8rem
- [x] FAQ: max-width 820px, shadow для открытого элемента
- [x] Final CTA: clamp font, ornament decoration
- [x] Footer: larger text, more padding

### Фаза 3 — UX-апгрейд ✅ (15.03.2026)

Конверсия, ясность оффера, доверие, информационная архитектура.

**Задачи:**
- [x] Desktop-навигация в шапке (ссылки + CTA кнопка, видна ≥1025px)
- [x] Бургер → только мобиль
- [x] Hero desc: конкретизировать оффер (что за продукт, кому, что получит)
- [x] Hero: вынести цену в отдельную строку
- [x] Hero: secondary CTA «Посмотреть пример» (anchor → #sample)
- [x] Values: заголовок + подзаголовок секции; развёрнутые описания карточек
- [x] Steps: новый заголовок «Всё проще, чем кажется»; reassurance-note
- [x] Sample: переформулировать на «Биография, а не расшифровка»; 2 CTA в блоке
- [x] Mid-CTA полоса после отзывов (тёмный фон, emotional hook + кнопка)
- [x] FAQ: переставить вопросы в конверсионный порядок
- [x] Final CTA: what-you-get список из 3 пунктов
- [x] Hero: убрать book-заглушку из первого экрана

### Фаза 4 — Наполнение ассетами ⏳ (ожидание клиента)

- [ ] Получить лого и разместить в nav/footer
- [ ] Получить hero-фото или обложку книги → разместить в hero
- [ ] Получить PDF-пример → разместить в `landing/sample.pdf` или S3
- [ ] Заменить все ссылки-заглушки на финальные
- [ ] Уточнить год в копирайте

### Фаза 5 — Деплой 🔜

- [ ] Создать `deploy/nginx-glava.conf` (согласовать с Агентом А)
- [ ] Настроить деплой: rsync или git pull → `/opt/glava/landing/`
- [ ] Проверить HTTPS (Let's Encrypt через certbot)
- [ ] Редирект www.glava.family → glava.family
- [ ] Проверить скорость загрузки (PageSpeed Insights)
- [ ] Проверить мобильный вид в реальном устройстве

---

## Структура файлов задачи

```
tasks/landing/
├── plan.md              ← этот файл
├── status.md            ← текущий статус и прогресс
├── tasks/
│   └── checklist.md     ← детальный чек-лист по фазам
├── jobs/
│   └── deploy.sh        ← скрипт деплоя лендинга на VPS
├── breadcrumbs/
│   └── 2026-03-15.md    ← заметки сессии 15.03.2026
└── docs/
    └── DESIGN_BRIEF.md  ← дизайн-бриф и описание блоков
```

---

## Ключевые файлы проекта

| Файл | Назначение |
|------|------------|
| `landing/index.html` | Весь лендинг — единый файл |
| `deploy/nginx-glava.conf` | Nginx конфиг (создать в фазе 5) |
| `tasks/landing/docs/DESIGN_BRIEF.md` | Дизайн-бриф |

---

## Ограничения (правила Агента Б)

- Не трогать Python-файлы, `main.py`, `pipeline_*.py`, `admin/blueprints/`
- Не менять `deploy/` и systemd конфиги без согласования с Агентом А
- Лендинг только в папке `landing/`
- Flask-маршруты в `cabinet/app.py` — только согласовывать с Агентом А

---

## Nginx-конфиг (план, согласовать с Агентом А)

```nginx
server {
    listen 80;
    server_name glava.family www.glava.family;
    return 301 https://glava.family$request_uri;
}

server {
    listen 443 ssl;
    server_name glava.family;

    root /opt/glava/landing;
    index index.html;

    ssl_certificate     /etc/letsencrypt/live/glava.family/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/glava.family/privkey.pem;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~* \.(css|js|png|jpg|jpeg|gif|svg|pdf|woff2?)$ {
        expires 30d;
        add_header Cache-Control "public";
    }
}
```
