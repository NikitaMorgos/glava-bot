# Support Bot — Статус

## Версия: v1.0 (задеплоено)

## Текущий статус: Задеплоено на prod (2026-03-27)

### Что готово
- [x] Каталог задачи создан
- [x] База знаний (черновик) — `docs/KNOWLEDGE_BASE.md`
- [x] Тон общения (черновик) — `docs/TONE_OF_VOICE.md`
- [x] System prompt — `support_prompt.py`
- [x] LLM модуль — `llm_support.py`
- [x] Интеграция в бота (`main.py`) — `/support` + групповой режим
- [x] Деплой на сервер (72.56.121.94)
- [x] Тестирование в групповом чате — работает
- [ ] Ревью базы знаний командой (Даша, Лена) — в процессе
- [ ] Заполнить `[УТОЧНИТЬ]` в KNOWLEDGE_BASE.md

### Модель
- **GPT-4o** (OpenAI)
- Себестоимость: ~$0.01–0.03 за диалог (10 обменов)

### Режимы работы
- **Личный чат:** команда `/support` → режим поддержки → текстовые сообщения → ответы AI → выход через `/start`
- **Групповой чат:** упоминание `@glava_voice_bot` или reply на сообщение бота → ответ AI

### Файлы
| Файл | Назначение |
|------|-----------|
| `support_prompt.py` | System prompt, собирается из KB + ToV с кешем 5 мин |
| `llm_support.py` | Вызов OpenAI, история диалога in-memory (сброс через 1ч) |
| `main.py` | Обработчики `/support`, `_handle_support_message` |
| `tasks/support-bot/docs/KNOWLEDGE_BASE.md` | База знаний (редактируется командой) |
| `tasks/support-bot/docs/TONE_OF_VOICE.md` | Тон общения |

### Конфигурация (.env)
```
OPENAI_API_KEY=...          # уже есть на сервере
SUPPORT_MODEL=gpt-4o        # опционально, по умолчанию gpt-4o
```

### Настройка группового чата
1. Добавить бота `@glava_voice_bot` в группу
2. Через `@BotFather` → `/mybots` → бот → **Bot Settings** → **Group Privacy** → **Turn off**
3. Обращаться к боту через `@glava_voice_bot вопрос` или reply на его сообщение
