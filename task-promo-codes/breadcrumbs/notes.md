# Хлебные крошки: Промо-коды

## 2026-03-24 — Реализация

### Ключевые решения

**JobQueue:** Сервис `glava.service` использует `venv/`, а не `.venv/`.
Пакет `python-telegram-bot[job-queue]` нужно устанавливать в правильный venv:
```bash
cd /opt/glava && venv/bin/pip install 'python-telegram-bot[job-queue]'
```
После установки планировщик `apscheduler` логирует: `Added job "personal_promos" to job store "default"`.

**calc_discount для fixed-типа:** Скидка типа `fixed` хранится в копейках (как и все цены в системе).
При создании через форму Лена вводит рубли — нужно учитывать при будущем рефакторинге UI (сейчас форма просит число, которое интерпретируется как kopecks).

**Персональный промо для users без telegram_id:** Функция `get_users_needing_personal_promo()` фильтрует `WHERE u.telegram_id IS NOT NULL` — пользователи без telegram_id пропускаются (нет куда слать бот-сообщение).

**Удаление промо из черновика:** `remove_promo_from_draft()` уменьшает `used_count` обратно — это позволяет пользователю поменять код до оплаты. После оплаты замена не предусмотрена.

**Окно планировщика:** `get_users_needing_personal_promo()` ищет пользователей в окне `NOW()-49h ... NOW()-47h`. При часовом интервале запуска планировщика окно гарантирует, что каждый пользователь попадёт ровно один раз (+-1ч погрешности).

### Структура таблицы promo_codes

```sql
id, code, type, discount_type, discount_value, max_uses, used_count,
expires_at, assigned_user_id, sent_at, created_by, created_at, is_active
```

- `type`: `general` | `personal`
- `discount_type`: `percent` | `fixed`
- `discount_value`: NUMERIC(10,2) — % или копейки
- `assigned_user_id`: только для personal, FK → users(id)
- `sent_at`: когда код отправлен боту; для personal срок = `sent_at + 24h`
- `created_by`: `auto` (планировщик) или имя пользователя админки

### Маршруты в adminке

| URL | Метод | Описание |
|-----|-------|----------|
| `/lena/promo` | GET | Список кодов + дашборд |
| `/lena/promo/new` | GET/POST | Форма создания |
| `/lena/promo/<id>/deactivate` | POST | Деактивация |
| `/lena/promo/<id>/activate` | POST | Реактивация |
| `/lena/promo/<id>/usages` | GET | История применений |
| `/lena/promo/export.csv` | GET | CSV-выгрузка |
