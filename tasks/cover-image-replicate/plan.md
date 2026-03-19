# Задача: AI-обложка книги через Replicate

## Цель
Заменить текстовую заглушку обложки PDF на полноценное AI-изображение через Replicate API (модель FLUX Schnell).

## Архитектура
- **replicate_client.py** — клиент для Replicate API. Функция `generate_cover_image(visual_style, character_name) -> bytes`.
- **pdf_book.py** — принимает `cover_image_bytes: bytes | None`. При наличии: full-bleed обложка с тёмным оверлеем и белым текстом поверх.
- **admin/blueprints/api.py** — `/api/send-book-pdf`: до генерации PDF вызывает Replicate, если задан `REPLICATE_API_TOKEN` и в `cover_spec` есть `visual_style`.
- **config.py** — добавлен `REPLICATE_API_TOKEN`.

## Провайдер-агностик
- Ключ `IMAGE_PROVIDER` в конфиге (по умолчанию `replicate`). При появлении `GOOGLE_API_KEY` — переключить на Imagen за 5 минут.

## Модель
- `black-forest-labs/flux-schnell` — быстрая, высококачественная, нет NSFW-проблем для портретных тематик.
- Формат: `2:3` (книжный), webp.

## Шаги
- [x] tasks/cover-image-replicate/ (plan.md, status.md)
- [ ] REPLICATE_API_TOKEN в .env + config.py + .env.example
- [ ] replicate_client.py
- [ ] pdf_book.py — full-bleed cover
- [ ] api.py — вызов Replicate перед PDF
- [ ] requirements.txt — добавить replicate
- [ ] Деплой + тест
