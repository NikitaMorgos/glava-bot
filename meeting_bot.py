"""
Бот записи онлайн-созвонов (Telemost, Zoom и др.).

Self-hosted: Playwright + Chromium (non-headless + Xvfb), захват аудио через pulseaudio.
Поддерживает:
- Ссылки от пользователя (прислал в бот)
- Ссылки, сгенерированные нами (Zoom API, Telemost API)

Зависимости: playwright, xvfb, pulseaudio (Linux), ffmpeg.
Установка: pip install playwright && playwright install chromium
           apt install xvfb
"""

import logging
import os
import subprocess
import tempfile
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Имена для pulseaudio (Linux)
PULSE_SINK_NAME = "glava_meeting_rec"
PULSE_SINK_MODULE = "module-null-sink"

# Номер виртуального дисплея Xvfb (должен быть свободен)
XVFB_DISPLAY = ":99"


def _start_xvfb() -> subprocess.Popen | None:
    """
    Запускает Xvfb на XVFB_DISPLAY если ещё не запущен.
    Возвращает Popen-объект или None если Xvfb недоступен/уже запущен.
    """
    try:
        # Проверяем, не занят ли дисплей уже
        r = subprocess.run(
            ["xdpyinfo", "-display", XVFB_DISPLAY],
            capture_output=True, timeout=3,
        )
        if r.returncode == 0:
            logger.info("Xvfb %s уже запущен", XVFB_DISPLAY)
            return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    try:
        proc = subprocess.Popen(
            ["Xvfb", XVFB_DISPLAY, "-screen", "0", "1280x720x24", "-ac"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1)
        logger.info("Xvfb запущен на %s (pid %s)", XVFB_DISPLAY, proc.pid)
        return proc
    except FileNotFoundError:
        logger.warning("Xvfb не найден: apt install xvfb")
        return None


def _is_zoom_url(url: str) -> bool:
    """Проверяет, что ссылка на Zoom."""
    url_lower = url.lower()
    return "zoom.us" in url_lower or "zoom.com" in url_lower


def _is_telemost_url(url: str) -> bool:
    """Проверяет, что ссылка на Yandex Telemost."""
    url_lower = url.lower()
    return "telemost.yandex" in url_lower or "telemost.ru" in url_lower


def _ensure_pulse_sink() -> bool:
    """
    Создаёт виртуальный sink в pulseaudio для захвата аудио.
    Возвращает True при успехе.
    """
    try:
        # Проверяем, есть ли уже
        r = subprocess.run(
            ["pactl", "list", "sinks", "short"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0 and PULSE_SINK_NAME in r.stdout:
            return True
        # Создаём
        r = subprocess.run(
            ["pactl", "load-module", PULSE_SINK_MODULE, f"sink_name={PULSE_SINK_NAME}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            logger.info("Pulse sink %s создан", PULSE_SINK_NAME)
            return True
        logger.warning("Не удалось создать pulse sink: %s", r.stderr or r.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning("pactl недоступен: %s", e)
    return False


def _unload_pulse_sink() -> None:
    """Выгружает модуль pulse sink."""
    try:
        r = subprocess.run(
            ["pactl", "list", "modules", "short"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode != 0:
            return
        for line in r.stdout.splitlines():
            if PULSE_SINK_NAME in line:
                parts = line.split()
                if parts:
                    mod_id = parts[0]
                    subprocess.run(
                        ["pactl", "unload-module", mod_id],
                        capture_output=True,
                        timeout=5,
                    )
                    break
    except Exception as e:
        logger.debug("unload pulse sink: %s", e)


def record_meeting(
    meeting_url: str,
    duration_sec: int = 1800,
    output_path: str | None = None,
    bot_name: str = "GlavaBot",
) -> str | None:
    """
    Подключается к встрече по URL, записывает аудио.

    Args:
        meeting_url: Ссылка на Zoom, Telemost или другую WebRTC-встречу.
        duration_sec: Максимальная длительность записи (по умолчанию 30 мин).
        output_path: Путь для сохранения аудио. Если None — временный файл.
        bot_name: Имя для отображения в meeting (если применимо).

    Returns:
        Путь к записанному аудиофайлу (.ogg) или None при ошибке.
    """
    if not meeting_url or not meeting_url.strip():
        logger.error("record_meeting: пустая ссылка")
        return None

    meeting_url = meeting_url.strip()
    if not meeting_url.startswith(("http://", "https://")):
        logger.error("record_meeting: неверный URL: %s", meeting_url[:50])
        return None

    # Платформа: pulseaudio только на Linux
    if os.name != "posix":
        logger.warning("record_meeting: pulseaudio работает только на Linux")
        return None

    if not _ensure_pulse_sink():
        logger.error("record_meeting: pulseaudio sink недоступен")
        return None

    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".ogg", prefix="meeting_")
        os.close(fd)

    env = os.environ.copy()
    env["PULSE_SINK"] = PULSE_SINK_NAME
    # Chrome в non-headless режиме выводит аудио через PulseAudio только при наличии дисплея
    env["DISPLAY"] = os.environ.get("DISPLAY", XVFB_DISPLAY)

    xvfb_proc = None
    recorder_proc = None
    ffmpeg_proc = None
    browser = None

    try:
        # Запускаем Xvfb если DISPLAY не задан снаружи
        if not os.environ.get("DISPLAY"):
            xvfb_proc = _start_xvfb()
            if not xvfb_proc:
                # Xvfb уже мог быть запущен ранее — проверим
                r = subprocess.run(
                    ["xdpyinfo", "-display", XVFB_DISPLAY],
                    capture_output=True, timeout=3,
                )
                if r.returncode != 0:
                    logger.error("record_meeting: Xvfb недоступен, установите: apt install xvfb")
                    return None

        # Запускаем запись аудио в фоне
        recorder_proc = subprocess.Popen(
            [
                "parec",
                f"--device={PULSE_SINK_NAME}.monitor",
                "--format=s16le",
                "--rate=44100",
                "--channels=1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        ffmpeg_proc = subprocess.Popen(
            [
                "ffmpeg",
                "-y",
                "-f", "s16le",
                "-ar", "44100",
                "-ac", "1",
                "-i", "pipe:0",
                "-c:a", "libopus",
                "-b:a", "64k",
                output_path,
            ],
            stdin=recorder_proc.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Запускаем браузер — non-headless с Xvfb для корректного вывода аудио в PulseAudio
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=[
                    "--autoplay-policy=no-user-gesture-required",
                    "--disable-features=AudioServiceOutOfProcess",
                    "--use-fake-ui-for-media-stream",
                    f"--alsa-output-device=pulse",
                    "--no-sandbox",
                ],
                ignore_default_args=["--mute-audio"],
                env=env,
            )
            context = browser.new_context(
                permissions=["microphone"],
                user_agent="Mozilla/5.0 (X11; Linux x86_64) GLAVA-Bot/1.0",
            )
            page = context.new_page()

            page.goto(meeting_url, wait_until="domcontentloaded", timeout=60000)

            # Ждём загрузки meeting (Telemost грузит iframe — нужно больше времени)
            extra_wait = 5 if _is_telemost_url(meeting_url) else 3
            time.sleep(5 + extra_wait)

            debug_join = os.environ.get("MEETING_JOIN_DEBUG", "").strip().lower() in ("1", "true", "yes")
            if debug_join:
                try:
                    page.screenshot(path="/tmp/meeting_join_debug.png")
                    logger.info("DEBUG: скриншот сохранён в /tmp/meeting_join_debug.png")
                    for i, frame in enumerate(page.frames):
                        try:
                            inputs_info = frame.evaluate("""() => {
                                const inputs = document.querySelectorAll('input, [contenteditable="true"]');
                                return Array.from(inputs).map(el => ({
                                    tag: el.tagName,
                                    name: el.name,
                                    id: el.id,
                                    placeholder: el.placeholder || '',
                                    type: el.type || '',
                                    value: (el.value || el.textContent || '').slice(0, 50)
                                }));
                            }""")
                            logger.info("DEBUG: frame %s (url=%s) inputs: %s", i, frame.url, inputs_info)
                        except Exception as e:
                            logger.info("DEBUG: frame %s: %s", i, e)
                except Exception as e:
                    logger.warning("DEBUG: не удалось сохранить отладку: %s", e)

            # Сначала заполняем имя (Telemost, Zoom — поле часто до кнопки «Войти»)
            # Telemost: placeholder может быть "Гость"; форма может быть в iframe
            name_selectors = [
                'input[placeholder*="Гость"]',
                'input[placeholder*="гость"]',
                'input[placeholder*="Guest"]',
                'input[name="name"]',
                'input[placeholder*="ame"]',
                'input[placeholder*="имя"]',
                'input[placeholder*="Имя"]',
                'input[placeholder*="имени"]',
                'input[placeholder*="называть"]',
                '#inputname',
                'input[type="text"]',
                '[data-testid="name-input"]',
                'input[autocomplete="name"]',
                '[contenteditable="true"]',
            ]

            def _try_fill_name(frame_or_page):
                for sel in name_selectors:
                    try:
                        loc = frame_or_page.locator(sel).first
                        if loc.is_visible(timeout=1000):
                            loc.fill(bot_name)
                            return True
                    except Exception:
                        continue
                return False

            filled = _try_fill_name(page)
            if not filled:
                for frame in page.frames:
                    if frame != page.main_frame and _try_fill_name(frame):
                        filled = True
                        break
            if filled:
                time.sleep(1)

            # Кнопки Join / Войти / Подключиться (в т.ч. в iframe)
            join_selectors = [
                'button:has-text("Join")',
                'button:has-text("Войти")',
                'button:has-text("Подключиться")',
                'a:has-text("Join")',
                'a:has-text("Открыть в браузере")',
                '[data-testid="join-meeting"]',
                'button[aria-label*="Join"]',
                'button:has-text("Войти в конференцию")',
            ]

            def _try_click_join(frame_or_page):
                for sel in join_selectors:
                    try:
                        btn = frame_or_page.locator(sel).first
                        if btn.is_visible(timeout=2000):
                            btn.click()
                            return True
                    except Exception:
                        continue
                return False

            if not _try_click_join(page):
                for frame in page.frames:
                    if frame != page.main_frame and _try_click_join(frame):
                        break
            time.sleep(3)

            # Повторно заполняем имя (Telemost может показать поле после клика «Войти»)
            _try_fill_name(page)
            for frame in page.frames:
                if frame != page.main_frame:
                    _try_fill_name(frame)

            # Записываем
            elapsed = 0
            while elapsed < duration_sec:
                time.sleep(10)
                elapsed += 10
                if elapsed % 60 == 0:
                    logger.info("Запись %s сек / %s", elapsed, duration_sec)

            context.close()
            browser.close()
            browser = None

        # Останавливаем запись
        if recorder_proc and recorder_proc.poll() is None:
            recorder_proc.terminate()
            recorder_proc.wait(timeout=5)
        if ffmpeg_proc and ffmpeg_proc.poll() is None:
            ffmpeg_proc.wait(timeout=5)

        if Path(output_path).exists() and Path(output_path).stat().st_size > 1000:
            logger.info("Запись сохранена: %s", output_path)
            return output_path
        logger.warning("Файл записи пуст или не создан: %s", output_path)

    except Exception as e:
        logger.exception("record_meeting error: %s", e)
    finally:
        if recorder_proc and recorder_proc.poll() is None:
            recorder_proc.terminate()
        if ffmpeg_proc and ffmpeg_proc.poll() is None:
            ffmpeg_proc.terminate()
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        if xvfb_proc and xvfb_proc.poll() is None:
            try:
                xvfb_proc.terminate()
            except Exception:
                pass
        _unload_pulse_sink()

    return None


def record_meeting_background(
    meeting_url: str,
    telegram_id: int,
    username: str | None,
    duration_sec: int = 1800,
) -> None:
    """
    Запускает запись в фоне, затем транскрибирует и передаёт в пайплайн.
    Вызывать из main.py после проверки оплаты.
    """
    import threading

    def _run():
        try:
            out = record_meeting(meeting_url, duration_sec=duration_sec)
            if not out:
                logger.warning("Запись встречи не удалась: %s", meeting_url[:50])
                return

            # Транскрипция — AssemblyAI, SpeechKit (через S3) или Whisper
            transcript = None
            api_key_aa = os.getenv("ASSEMBLYAI_API_KEY", "")
            api_key_ya = os.getenv("YANDEX_API_KEY", "")

            if api_key_aa:
                from assemblyai_client import transcribe_via_assemblyai
                transcript = transcribe_via_assemblyai(out, api_key=api_key_aa)
            elif api_key_ya:
                # SpeechKit требует файл в S3 — загружаем во временный ключ
                import uuid
                import storage
                temp_key = f"temp/meeting_{uuid.uuid4().hex}.ogg"
                storage.upload_file_to_key(out, temp_key)
                try:
                    from transcribe import transcribe_audio
                    transcript = transcribe_audio(out, storage_key=temp_key)
                finally:
                    try:
                        storage.delete_object(temp_key)
                    except Exception:
                        pass
            else:
                from transcribe import transcribe_audio
                transcript = transcribe_audio(out, storage_key=None)  # Whisper

            if not transcript or not transcript.strip():
                logger.warning("Пустой транскрипт встречи")
                return

            # Пайплайн — n8n или fallback
            n8n_url = os.getenv("N8N_WEBHOOK_PHASE_A", "").strip()
            if n8n_url:
                from pipeline_n8n import trigger_phase_a_background
                trigger_phase_a_background(
                    telegram_id=telegram_id,
                    transcript=transcript,
                    character_name="",
                    draft_id=0,
                    username=username or "",
                )
                logger.info("Транскрипт встречи передан в n8n Phase A")
            else:
                from pipeline_mymeet_bio import run_pipeline_from_transcript_sync
                run_pipeline_from_transcript_sync(
                    telegram_id=telegram_id,
                    username=username,
                    transcript=transcript,
                    source_label="meeting-bot",
                )

            # Удаляем временный файл
            if out.startswith(tempfile.gettempdir()):
                try:
                    os.unlink(out)
                except OSError:
                    pass
        except Exception as e:
            logger.exception("record_meeting_background: %s", e)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    logger.info("Запись встречи запущена в фоне для user %s", telegram_id)
