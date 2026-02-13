"""Проверка голосовых в БД — кто сколько, длительность."""
import db

for c in db.get_all_clients():
    _, voices, _ = db.get_user_all_data(c["telegram_id"])
    print(f"\n{c['telegram_id']} @{c.get('username') or '-'}:")
    for i, v in enumerate(voices, 1):
        dur = v.get("duration", "?")
        print(f"  {i}. {dur} сек  transcript={'есть' if v.get('transcript') else 'нет'}")
