# Support Bot — Чек-лист

## Разработка
- [x] Каталог задачи по AGENTS протоколу
- [x] docs/KNOWLEDGE_BASE.md — черновик из кода и лендинга
- [x] docs/TONE_OF_VOICE.md — правила общения
- [x] support_prompt.py — system prompt
- [x] llm_support.py — вызов LLM + история в памяти
- [x] Интеграция в main.py — /support + групповой режим
- [x] Обновить _post_init (команда /support в меню)
- [x] Обновить AGENTS.md

## Деплой
- [x] scp файлов на сервер (72.56.121.94)
- [x] Создать каталог tasks/support-bot/ на сервере
- [x] systemctl restart glava
- [x] Проверить OPENAI_API_KEY на сервере
- [x] Проверить статус — active (running)
- [x] Smoke test в групповом чате — работает

## Ревью контента (команда)
- [ ] Проверить и дополнить KNOWLEDGE_BASE.md (цены, сроки, FAQ)
- [ ] Проверить TONE_OF_VOICE.md
- [ ] Заполнить [УТОЧНИТЬ] в базе знаний
- [ ] Указать контакт живого оператора для эскалации
