# Диаризация — пошаговая инструкция

## Что это даёт

При экспорте клиента транскрипция будет с разметкой по спикерам:
```
Speaker 00: Здравствуйте, расскажите о себе.
Speaker 01: Конечно, меня зовут...
Speaker 00: А как давно вы занимаетесь этим?
```

---

## Требования перед установкой

- **Python 3.10, 3.11 или 3.12** — лучше не 3.14 (у многих пакетов нет готовых сборок)
- **Microsoft C++ Build Tools** — если при `pip install` появится ошибка «Microsoft Visual C++ 14.0 required»:
  1. Скачай: https://visualstudio.microsoft.com/visual-cpp-build-tools/
  2. Установи компонент «Desktop development with C++»

---

## Шаг 1. Установка зависимостей

### Вариант А — через bat-файл (проще)

1. Дважды кликни по файлу **`install_diarization.bat`**
2. Дождись окончания (2–5 минут)
3. При успехе увидишь «Готово»

### Вариант Б — вручную в терминале

1. Открой PowerShell или CMD в папке GLAVA
2. Выполни:
   ```
   venv\Scripts\activate
   pip install Resemblyzer scikit-learn
   ```
3. Дождись окончания установки

Транскрипция пойдёт через Whisper (если установлен) или SpeechKit (если задан YANDEX_API_KEY).

---

## Шаг 2. FFmpeg (если ещё не установлен)

Диаризация использует FFmpeg для работы с аудио.

- **Проверка:** открой новый терминал и введи `ffmpeg -version`
- Если команда не найдена:
  1. Скачай FFmpeg: https://ffmpeg.org/download.html (Windows builds)
  2. Распакуй и добавь папку `bin` в PATH

---

## Шаг 3. Экспорт с диаризацией

1. Узнай `telegram_id` клиента (например, из списка: `python export_client.py`)
2. Выполни:
   ```
   venv\Scripts\python.exe export_client.py TELEGRAM_ID --diarize
   ```
   Например:
   ```
   venv\Scripts\python.exe export_client.py 123456789 --diarize
   ```

3. Результат — в папке `exports/client_TELEGRAM_ID_username/`
   - `transcript.txt` — транскрипция с разметкой по спикерам

---

## Возможные ошибки

| Ошибка | Решение |
|--------|---------|
| `Microsoft Visual C++ 14.0 required` | Установи [Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) с компонентом «Desktop development with C++» |
| `No module named 'resemblyzer'` | Запусти `pip install Resemblyzer scikit-learn` |
| `ffmpeg not found` | Установи FFmpeg и добавь в PATH |
| Python 3.14 — сборка падает | Создай venv с Python 3.11 или 3.12 |
| Долгая обработка | Нормально. Минута аудио ≈ 1–2 минуты на CPU |

---

## Без регистрации

Диаризация работает через Resemblyzer — без HuggingFace и без создания аккаунтов.
