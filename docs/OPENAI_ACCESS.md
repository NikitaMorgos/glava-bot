# Доступ к OpenAI API (ChatGPT) для скриптов GLAVA

Скрипты, которые вызывают **OpenAI API** (формирование биодокумента из транскрипта, генерация уточняющих вопросов), используют ключ `OPENAI_API_KEY` из `.env`.

## Доступ из России

**Прямой доступ к API OpenAI из РФ часто недоступен или нестабилен:** соединение обрывается (WinError 10054, «удалённый хост разорвал подключение»), запросы не доходят или таймаутятся.

**Рекомендация:** запускать такие скрипты **в среде, откуда OpenAI API доступен**:

- **Сервер за рубежом** (VPS/облако в регионе, где API не блокируется) — предпочтительно.
- **VPN**, если он стабильно открывает доступ к `api.openai.com` (не все VPN с этим справляются).

## Какие скрипты затронуты

- `scripts/run_assembly_to_bio.py` — прогон транскрипта Assembly через промпт формирования документа.
- `scripts/run_llm_bio.py` — генерация `bio_story.txt` из `transcript.txt`.
- Пайплайны с шагом «биография + уточняющие вопросы»:  
  `pipeline_transcribe_bio.py`, `pipeline_assemblyai_bio.py`, `pipeline_plaud_bio.py`, `pipeline_mymeet_bio.py`.

Все они вызывают `llm_bio.process_transcript_to_bio` и/или `llm_bio.generate_clarifying_questions`.

## Качество биографии (модель и параметры)

Чтобы результат через API был ближе к веб-интерфейсу ChatGPT:

- **Модель:** по умолчанию используется **gpt-4o**. Не использовать облегчённые модели (gpt-4o-mini) для биографии — они чаще искажают имена и дописывают шаблонные фразы. Переопределение в `.env`: `OPENAI_BIO_MODEL=gpt-4o` или `gpt-4-turbo`, `gpt-4`.
- **Температура:** 0.2 (низкая — меньше «литературизации» и искажения фактов).
- **max_tokens:** 8192 (достаточно для длинной биографии без обрезки).
- **Streaming:** отключён, чтобы модель могла планировать текст целиком.
- В системном промпте добавлена **финальная проверка**: сверка имён и мест с транскриптом, запрет придумывать факты.

## Если запускаете локально и получаете обрыв соединения

1. Убедитесь, что ключ `OPENAI_API_KEY` в `.env` верный.
2. Если вы в РФ — перенесите запуск на **сервер за рубежом** или включите рабочий **VPN** и повторите.
3. Для длинных транскриптов можно сократить вход:  
   `$env:BIO_TRANSCRIPT_MAX_CHARS="12000"` (PowerShell) перед запуском — тогда запрос меньше и иногда проходит стабильнее.

В коде уже есть повторные попытки (до 3) и увеличенный таймаут; если после этого ошибка сохраняется, причина, как правило, в недоступности API из текущей сети.

---

## Запуск на сервере (пошагово)

Сервер должен иметь доступ в интернет к `api.openai.com` (обычно VPS за рубежом). Ниже — как запустить прогон транскрипта Assembly через ChatGPT (формирование документа).

### 1. Проект на сервере

Если репозиторий уже есть на сервере (git):

```bash
cd /путь/к/проекту/GLAVA
git pull
```

Если копируете вручную — скопируйте на сервер всю папку проекта (или как минимум: `scripts/`, `llm_bio.py`, `biographical_prompt.py`, `clarifying_questions_prompt.py` и каталог `exports/` с данными).

#### Как скопировать обновлённые файлы с ПК на сервер

Подставьте свой логин и IP сервера (например `root@72.56.121.94`). Если подключаетесь не как `root`, замените `root` на свой логин. По запросу введите пароль.

**Только скрипты био (OpenAI) — без бота:**

**На ПК (PowerShell):**
```powershell
cd "C:\Users\user\Dropbox\Public\Cursor\GLAVA"

scp llm_bio.py biographical_prompt.py config.py root@72.56.121.94:/tmp/
scp scripts/run_assembly_to_bio.py root@72.56.121.94:/tmp/
```

**На сервере:**
```bash
mv /tmp/llm_bio.py /tmp/biographical_prompt.py /tmp/config.py /opt/glava/
mv /tmp/run_assembly_to_bio.py /opt/glava/scripts/
```

После этого можно запускать `python3 scripts/run_assembly_to_bio.py` из `/opt/glava` с активированным `.venv`.

**Деплой бота (main.py и команда /online):**

Чтобы на сервере работали обновления бота, в том числе команда `/online`, нужно копировать не только `main.py` и `config.py`, но и модули с текстами и клавиатурами: иначе при старте будет `ImportError` (например `cannot import name 'ONLINE_MEETING_INTRO_MSG'`).

**На ПК (PowerShell):**
```powershell
cd "C:\Users\user\Dropbox\Public\Cursor\GLAVA"

scp main.py config.py root@72.56.121.94:/tmp/
scp prepay\messages.py prepay\keyboards.py root@72.56.121.94:/tmp/
```

**На сервере:**
```bash
mv /tmp/main.py /tmp/config.py /opt/glava/
mv /tmp/messages.py /tmp/keyboards.py /opt/glava/prepay/
sudo systemctl restart glava
sudo systemctl status glava
```

Если добавлялись другие файлы для онлайн-встреч (например `mymeet_client.py`, `pipeline_mymeet_bio.py`), их тоже нужно залить на сервер в соответствующие каталоги.

#### Бот не запускается (status=1/FAILURE, activating auto-restart)

1. **Увидеть ошибку** — на сервере:
   ```bash
   journalctl -u glava -n 100 --no-pager
   ```
   В конце будет трейсбек Python. Или запуск вручную:
   ```bash
   cd /opt/glava
   ./venv/bin/python main.py
   ```
   (Если окружение у тебя называется `.venv`, то: `./.venv/bin/python main.py`.)

2. **Путь к venv** — юнит systemd использует `/opt/glava/venv/bin/python`. Если на сервере папка называется `.venv`, либо переименуй в `venv`, либо поправь юнит:
   ```bash
   sudo nano /etc/systemd/system/glava.service
   ```
   Строку `ExecStart=/opt/glava/venv/bin/python main.py` замени на:
   `ExecStart=/opt/glava/.venv/bin/python main.py`
   Затем: `sudo systemctl daemon-reload && sudo systemctl restart glava`.

3. **Частые ошибки:** `ImportError` / нет константы из `prepay.messages` — залить актуальные `prepay/messages.py` и `prepay/keyboards.py`. `ModuleNotFoundError` — установить зависимости в нужный venv: `./venv/bin/pip install -r requirements.txt` (из `/opt/glava`). Отсутствует `.env` или переменная — создать/дописать `/opt/glava/.env`.

#### Как выдать пользователю ссылку на разговор из бота

Чтобы по команде `/online` в боте была кнопка **«Получить ссылку на встречу»** и бот отдавал одну и ту же ссылку (на которую MyMeet потом подключается для записи), нужна **постоянная ссылка на комнату** и переменная в `.env` на сервере.

**Шаг 1. Создать комнату и получить ссылку**

Подойдёт любая платформа, которую поддерживает MyMeet (Jitsi, Google Meet, Zoom, Яндекс Телемост и т.д.). Самый простой вариант без регистрации:

- **Jitsi:** откройте в браузере `https://meet.jit.si/НазваниеКомнаты` (например `https://meet.jit.si/GlavaInterview`). Ссылка на эту комнату — и есть ваша постоянная ссылка. Имя комнаты можно менять, главное — потом использовать один и тот же URL.

Либо создайте встречу в Google Meet / Zoom / Телемост и скопируйте ссылку «присоединиться».

**Шаг 2. Прописать ссылку на сервере**

В `.env` в корне проекта на сервере (`/opt/glava/.env`) добавьте или отредактируйте:

```bash
TELEMOST_MEETING_LINK=https://meet.jit.si/GlavaInterview
```

Подставьте свою ссылку (обязательно `https://...`).

**Шаг 3. Перезапустить бота**

```bash
sudo systemctl restart glava
```

**Что получится:** пользователь пишет `/online` → видит кнопку «🔗 Получить ссылку на встречу» → нажимает → бот присылает эту ссылку и сразу подключает запись MyMeet к этой комнате. Пользователь переходит по ссылке, разговаривает; после окончания встречи транскрипт уходит в пайплайн.

Если `TELEMOST_MEETING_LINK` не задана, кнопки «Получить ссылку» не будет — пользователь может только **прислать свою ссылку** текстом (создал встречу сам и вставил ссылку в чат бота).

### 2. Транскрипт и ключ API

- **Транскрипт** должен лежать по пути:
  ```
  exports/client_605154_unknown/transcript_assemblyai_diarized.txt
  ```
  Если на сервере своей структуры нет — создайте каталог и положите файл:
  ```bash
  mkdir -p exports/client_605154_unknown
  # затем скопируйте с локальной машины transcript_assemblyai_diarized.txt в эту папку
  ```

- **Ключ OpenAI** — в файле `.env` в корне проекта строка:
  ```
  OPENAI_API_KEY=sk-...ваш_ключ...
  ```
  Создайте или отредактируйте `.env`:
  ```bash
  echo 'OPENAI_API_KEY=sk-ваш_ключ' > .env
  # или: nano .env
  ```

### 3. Зависимости Python

На сервере должен быть Python 3.10+. Установите клиент OpenAI:

```bash
pip install openai
```

Если используете виртуальное окружение:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
# или на Windows на сервере: .venv\Scripts\activate
pip install openai
```

### 4. Команда запуска

Из **корня проекта** GLAVA выполните:

```bash
cd /путь/к/проекту/GLAVA
python3 scripts/run_assembly_to_bio.py
```

Или, если вызываете через `python`:

```bash
python scripts/run_assembly_to_bio.py
```

Скрипт прочитает `exports/client_605154_unknown/transcript_assemblyai_diarized.txt`, отправит текст в OpenAI API и запишет результат в:

```
exports/client_605154_unknown/bio_from_assembly.txt
```

В консоль выведется начало этого файла. Полный текст — в указанном файле.

### 5. (По желанию) Ограничить длину транскрипта

Если хотите прогнать только первые 12 000 символов (меньше шанс таймаута при очень длинном интервью):

```bash
export BIO_TRANSCRIPT_MAX_CHARS=12000
python3 scripts/run_assembly_to_bio.py
```

### 6. Забрать результат на локальную машину

После успешного запуска скачайте с сервера файл результата, например по SCP:

```bash
scp user@сервер:/путь/к/GLAVA/exports/client_605154_unknown/bio_from_assembly.txt ./
```

Или через SFTP/файловый менеджер — скопируйте `exports/client_605154_unknown/bio_from_assembly.txt`.

### 7. Генерация уточняющих вопросов (по готовому bio)

После того как получен `bio_from_assembly.txt`, можно сгенерировать список уточняющих вопросов для следующего интервью:

```bash
cd /opt/glava
source .venv/bin/activate
python3 scripts/run_clarifying_questions.py
```

Скрипт читает `exports/client_605154_unknown/bio_from_assembly.txt` и пишет результат в `exports/client_605154_unknown/clarifying_questions.txt`. На сервер нужно предварительно скопировать `scripts/run_clarifying_questions.py` (как и другие скрипты).
