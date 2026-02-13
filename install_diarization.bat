@echo off
chcp 65001 >nul
echo ========================================
echo   Установка диаризации для GLAVA
echo ========================================
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Ошибка: venv не найден. Сначала создай: python -m venv venv
    pause
    exit /b 1
)

echo Устанавливаю librosa, scikit-learn ^(диаризация без Resemblyzer^)...
echo ^(может занять 2-5 минут^)
echo.
venv\Scripts\pip.exe install librosa scikit-learn

if %errorlevel% neq 0 (
    echo.
    echo Ошибка установки. Проверь подключение к интернету.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Готово.
echo ========================================
echo.
echo Экспорт с диаризацией:
echo   venv\Scripts\python.exe export_client.py TELEGRAM_ID --diarize
echo.
echo Замени TELEGRAM_ID на ID клиента ^(число^).
echo Транскрипция: Whisper или SpeechKit ^(если YANDEX_API_KEY задан^).
echo.
pause
