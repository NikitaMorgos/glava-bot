# Чеклист: корпоративная почта glava.family

## Подготовка
- [x] Определить панель управления DNS домена glava.family → **nic.ru**
- [x] Зарегистрироваться в Яндекс 360 (организация СМЗ, не требует ИП/ООО)
- [x] Добавить домен `glava.family` в Яндекс 360

## DNS-записи
- [x] TXT — подтверждение владения `yandex-verification: 89bb40eabb881d7b`
- [x] Нажать «Проверить домен» в Яндекс 360 — подтверждён ✅
- [x] MX — `mx.yandex.net.` приоритет 10 (старых MX не было)
- [x] TXT SPF — `v=spf1 include:_spf.yandex.net ~all`
- [x] TXT DKIM — добавлен в nic.ru (исправлена ошибка `l` vs `I`)
- [x] Яндекс 360 → «DKIM-подпись настроена верно» ✅
- [x] TXT DMARC — `v=DMARC1; p=none; rua=mailto:postmaster@glava.family`

## Создание ящиков
- [x] Основной ящик: `glava-family@glava.family` (аккаунт Моргось Никита)
- [x] Псевдоним: `nikita@glava.family`
- [x] Псевдоним: `info@glava.family`
- [ ] `postmaster@glava.family` — опционально, добавить при необходимости

## Проверка
- [x] `nslookup -type=MX glava.family` → `mx.yandex.net` ✅
- [x] `nslookup -type=TXT glava.family` → SPF + yandex-verification ✅
- [x] `nslookup -type=TXT mail._domainkey.glava.family` → DKIM ✅
- [x] `nslookup -type=TXT _dmarc.glava.family` → DMARC ✅
- [x] Исходящее письмо с `glava-family@glava.family` дошло на Gmail ✅
- [x] Входящее на `info@glava.family` принимается ✅
- [ ] Зарегистрировать домен в Google Postmaster Tools (улучшит репутацию отправителя)
