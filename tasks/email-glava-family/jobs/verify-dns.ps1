# verify-dns.ps1 — проверка DNS-записей glava.family для Яндекс 360
# Запуск: .\tasks\email-glava-family\jobs\verify-dns.ps1

$domain = "glava.family"

Write-Host "`n=== MX ===" -ForegroundColor Cyan
Resolve-DnsName -Name $domain -Type MX | Select-Object NameExchange, Preference

Write-Host "`n=== TXT (SPF / DKIM-подтверждение) ===" -ForegroundColor Cyan
Resolve-DnsName -Name $domain -Type TXT | Select-Object Strings

Write-Host "`n=== DKIM ===" -ForegroundColor Cyan
try {
    Resolve-DnsName -Name "mail._domainkey.$domain" -Type TXT | Select-Object Strings
} catch {
    Write-Host "DKIM-запись не найдена (ещё не добавлена)" -ForegroundColor Yellow
}

Write-Host "`n=== DMARC ===" -ForegroundColor Cyan
try {
    Resolve-DnsName -Name "_dmarc.$domain" -Type TXT | Select-Object Strings
} catch {
    Write-Host "DMARC-запись не найдена (ещё не добавлена)" -ForegroundColor Yellow
}

Write-Host "`nОнлайн-проверка: https://mxtoolbox.com/SuperTool.aspx`n" -ForegroundColor Green
