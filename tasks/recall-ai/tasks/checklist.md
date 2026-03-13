# Чеклист подключения Recall.ai

## Шаг 1 — Регистрация

- [ ] Перейти на https://www.recall.ai/
- [ ] Нажать "Get Started" → зарегистрироваться (email + Google)
- [ ] Создать организацию / проект

## Шаг 2 — API ключ

- [ ] Перейти: Dashboard → Settings → API Keys
- [ ] Нажать "Create new key"
- [ ] Скопировать ключ (показывается один раз)

## Шаг 3 — Конфигурация

```env
# .env (локально и на сервере)
RECALL_API_KEY=your_recall_api_key_here
RECALL_REGION=us-east-1
TRANSCRIBER=recall
```

На сервере:
```bash
nano /opt/glava/.env
# добавить RECALL_API_KEY и RECALL_REGION
sudo systemctl restart glava
```

## Шаг 4 — Проверка

```bash
# Проверить что бот видит ключ
journalctl -u glava -n 20

# Тест через /online в Telegram — отправить ссылку на Google Meet
```

## Шаг 5 — Мониторинг первого звонка

```bash
# Смотреть логи в реальном времени
journalctl -u glava -f
```

Ожидаемые логи:
```
recall bot created, bot_id=...
recall status: joining_call
recall status: in_call_recording  
recall status: done
Биография сохранена: exports/client_.../bio_story.txt
```
