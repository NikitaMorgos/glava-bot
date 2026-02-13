# Настройка диаризации (разделение по спикерам)

Диаризация размечает транскрипцию интервью по спикерам: «Speaker 00», «Speaker 01» и т.д.

## Использование

```
python export_client.py TELEGRAM_ID --diarize
```

Результат в `transcript.txt`:

```
Speaker 00: Здравствуйте, расскажите немного о себе.
Speaker 01: Конечно, меня зовут Иван...
Speaker 00: А как давно вы занимаетесь этим?
```

---

## Вариант 1: Resemblyzer (без регистрации)

Работает без HuggingFace и любой регистрации.

### Шаги

1. **Установи зависимости:**
   ```
   pip install Resemblyzer scikit-learn faster-whisper
   ```

2. **FFmpeg** — должен быть в системе (для конвертации аудио).

3. **Готово.** Запускай:
   ```
   python export_client.py TELEGRAM_ID --diarize
   ```

Модель Resemblyzer (~5 MB) встроена в пакет, загрузок из интернета не требуется.

---

## Вариант 2: pyannote (с HuggingFace, точнее)

Если нужна более точная диаризация и есть аккаунт HuggingFace:

1. Создай токен на [hf.co/settings/tokens](https://hf.co/settings/tokens)
2. Прими условия: [segmentation-3.0](https://hf.co/pyannote/segmentation-3.0) и [speaker-diarization-3.0](https://hf.co/pyannote/speaker-diarization-3.0)
3. Добавь в `.env`: `HUGGINGFACE_TOKEN=hf_xxxx`
4. `pip install pyannote.audio`

При наличии `HUGGINGFACE_TOKEN` бот будет использовать pyannote вместо Resemblyzer.

---

## Требования

- **Python 3.10+**
- **FFmpeg** — в PATH
- **PyTorch** — Resemblyzer его подтягивает

Обработка идёт на CPU (медленнее, но без GPU работает).
