# Полный тестовый прогон Корольковой (Python-пайплайн, prompts/pipeline_config.json)
# Требует: ANTHROPIC_API_KEY; для обложки — REPLICATE_API_TOKEN (опционально)
# Запуск из корня репозитория:  powershell -File scripts/_run_korolkova_stage1_to_4.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$Transcript = "exports/korolkova_combined_raw.txt"
if (-not (Test-Path $Transcript)) {
    Write-Host "[ERROR] Нет объединённого транскрипта: $Transcript (собери exports/korolkova/*.txt)"
    exit 1
}

Write-Host "[1/4] Stage1 Cleaner + Fact Extractor"
python scripts/_run_korolkova.py --transcript $Transcript
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/4] Stage2 Historian + Ghostwriter + Fact checker"
python scripts/test_stage2_korolkova.py --fact-map exports/korolkova_fact_map_v2.json --transcript exports/korolkova_cleaned_transcript.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$book = Get-ChildItem exports/korolkova_book_FINAL_*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$fc = Get-ChildItem exports/korolkova_fc_report_iter*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $book -or -not $fc) {
    Write-Host "[ERROR] Не найдены выходы Stage2 (korolkova_book_FINAL_*, korolkova_fc_report_*)"
    exit 1
}

Write-Host "[3/4] Stage3 Literary editor + Proofreader"
python scripts/test_stage3.py --prefix korolkova --book-draft $($book.FullName) --fc-warnings $($fc.FullName) --fact-map exports/korolkova_fact_map_v2.json
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$pr = Get-ChildItem exports/korolkova_proofreader_report_*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $pr) {
    Write-Host "[ERROR] Нет korolkova_proofreader_report_*.json после Stage3"
    exit 1
}

Write-Host "[4/4] Stage4 Layout + QA + cover"
python scripts/test_stage4_karakulina.py `
    --allow-legacy-input `
    --proofreader-report $($pr.FullName) `
    --fact-map exports/korolkova_fact_map_v2.json `
    --photos-dir exports/korolkova `
    --prefix korolkova `
    --subject-profile exports/korolkova_stage4_subject.json
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[DONE] Королькова Stage1-4 завершён"
