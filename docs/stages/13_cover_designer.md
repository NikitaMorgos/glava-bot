# Этап 13 — Дизайнер обложки (Cover Designer)

> **ID:** `13_cover_designer`  
> **Версия промпта:** v2.0  
> **Статус:** 🟢 Стабильный  
> **Обновлён:** 2026-03-31  

---

## Для Даши — что делает этот агент

### Роль
Выбирает лучшее фото для обложки, формулирует промпт для генерации тушевого портрета (через Replicate / nano-banana-2), и задаёт всю типографику и цветовую схему обложки.  
Работает в **два вызова**: первый — арт-дирекция (выбор фото + промпт для Replicate), второй — валидация сгенерированного портрета.

### Что должно быть в хорошем результате
- [ ] Выбрано фото с хорошо видимым лицом (не групповое, не спиной)
- [ ] Промпт для Replicate соответствует **возрасту на выбранном фото** (не «пожилая женщина» если на фото молодая)
- [ ] Три зоны обложки не пересекаются: верх (имя) / центр (портрет) / низ (годы + лого)
- [ ] Годы жизни вынесены вниз, не поверх портрета
- [ ] Второй вызов: APPROVED если портрет узнаваем и в стиле ink sketch

### Типичные ошибки и как их ловить
| Симптом | Вероятная причина | Что поправить |
|---------|-------------------|---------------|
| Промпт описывает «пожилую» женщину, а фото — молодая | Агент берёт возраст из биографии, а не из фото | Правило: «описывай возраст человека КАК НА ВЫБРАННОМ ФОТО, не как в конце жизни» |
| Текст наезжает на портрет | Зоны не заданы жёстко | Правило 3-зонной компоновки — не убирать |
| Второй вызов всегда APPROVED даже при плохом портрете | Агент не критичен | Ужесточить критерии валидации: конкретные признаки «не утверждать если…» |

### На что смотреть при написании промпта
- **Обязательно:** правило age-matching (возраст = возраст на фото)
- **Обязательно:** описание 3-зон и правило «текст никогда не поверх портрета»
- **Нельзя убирать:** схему двух вызовов — без второго вызова нет валидации
- **Помогает:** конкретный пример хорошего и плохого промпта для Replicate

### Как проверить результат вручную
1. Открыть `exports/project_stage4_cover_designer_call1_*.json`
2. Проверить `portrait_generation.image_gen_prompt` — соответствует ли возраст фото?
3. Открыть `exports/project_stage4_cover_portrait_*.webp` — похоже ли на человека?
4. Сравнить с референс-фото вручную
5. Красный флаг: в промпте слова «elderly», «old woman» при молодом фото

---

## Для разработки — техническая спецификация

### Место в пайплайне
```
[Фото из manifest.json] → [13 COVER DESIGNER call1] → [Replicate nano-banana-2]
                                                      → [13 COVER DESIGNER call2: валидация]
                                                      → [15 Art Director]
```

### Входные данные (call 1)

```json
{
  "project_id": "string",
  "subject": {"name": "...", "birth_year": 1920, "death_year": 2005, "subtitle": "..."},
  "photos": [{"photo_id": "photo_002", "caption": "...", "created_at": "..."}],
  "book_summary": "string — 2-3 предложения о герое"
}
```

### Выходные данные (call 1)

```json
{
  "selected_photo": {"photo_id": "photo_002", "reason": "..."},
  "portrait_generation": {
    "image_gen_prompt": "Ink sketch portrait of middle-aged woman...",
    "negative_prompt": "...",
    "reference_photo_id": "photo_002",
    "aspect_ratio": "3:4"
  },
  "cover_composition": {
    "background_color": "#faf6f0",
    "typography": {"surname": {...}, "first_name": {...}},
    "cover_layout": {"zones": {"top": {...}, "center": {...}, "bottom": {...}}}
  }
}
```

### Генерация портрета (между call1 и call2)

```python
# scripts/test_stage4_*.py  — run_replicate_ink_sketch()
ref_photo_id = pg.get("reference_photo_id")
ref_photo = next(p for p in photos if p["id"] == ref_photo_id)
ref_image_bytes = Path(ref_photo["local_path"]).read_bytes()

portrait_bytes = run_replicate_ink_sketch(image_gen_prompt, ref_image_bytes)
# → replicate_client.generate_ink_sketch_portrait()
# → google/nano-banana-2 (с референсом)
# → fallback: FLUX Schnell (без референса) если nano-banana-2 недоступен
```

> ⚠️ Если `reference_image_bytes=None` — nano-banana-2 не используется, идёт FLUX Schnell без сходства с оригиналом. Всегда передавай байты фото.

### Конфигурация

```json
{
  "cover_designer": {
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 12000,
    "temperature": 0.65,
    "prompt_file": "13_cover_designer_v2.md",
    "_vision": true
  }
}
```

**Почему такие параметры:**
- `temperature: 0.65` — нужна творческая вариативность при выборе цветов и стиля
- `_vision: true` — агент смотрит на фотографии (base64)
- `max_tokens: 12000` — cover_composition содержит много вложенных полей

### Replicate: nano-banana-2

| | |
|--|--|
| Модель | `google/nano-banana-2` |
| Тип | Image-to-image (ink sketch из референс-фото) |
| Fallback | `black-forest-labs/flux-schnell` (text-to-image) |
| Retry | 3 попытки × 30 сек паузы при `Service unavailable` |
| Время генерации | ~30–60 сек |

### Известные ограничения
- nano-banana-2 периодически недоступен (высокая нагрузка) — fallback на FLUX, портрет без сходства
- call2 слишком мягкий — почти всегда возвращает APPROVED; нужно ужесточить критерии

### История изменений

| Версия | Дата | Что изменилось |
|--------|------|----------------|
| v1.0 | 2026-03-06 | Первая версия (Даша) |
| v2.0 | 2026-03-31 | Age-matching, 3-зонная компоновка, убран декор года поверх портрета |
