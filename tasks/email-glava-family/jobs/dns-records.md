# Готовые DNS-записи для glava.family → Яндекс 360

Вставляй по одной в панель DNS-провайдера.
`<КОД>` и `<DKIM_КЛЮЧ>` — заменить на значения из Яндекс 360.

---

## 1. Подтверждение владения (заменить <КОД>)

```
Тип:    TXT
Хост:   @
Значение: yandex-verification: <КОД_ИЗ_ЯНДЕКС_360>
TTL:    3600
```

---

## 2. MX — маршрутизация почты

```
Тип:      MX
Хост:     @
Значение: mx.yandex.net.
Приоритет: 10
TTL:      3600
```

> Перед добавлением удали все старые MX-записи для @

---

## 3. SPF — защита от спуфинга

```
Тип:    TXT
Хост:   @
Значение: v=spf1 include:_spf.yandex.net ~all
TTL:    3600
```

> На домене должна быть ровно одна TXT-запись с v=spf1

---

## 4. DKIM — цифровая подпись (заменить <DKIM_КЛЮЧ>)

```
Тип:    TXT
Хост:   mail._domainkey
Значение: v=DKIM1; k=rsa; p=<DKIM_КЛЮЧ_ИЗ_ЯНДЕКС_360>
TTL:    3600
```

> Полный ключ берётся в: Яндекс 360 → Домен → DNS-записи → DKIM

---

## 5. DMARC — политика (можно добавить сразу)

```
Тип:    TXT
Хост:   _dmarc
Значение: v=DMARC1; p=none; rua=mailto:postmaster@glava.family
TTL:    3600
```

---

## Команды проверки (запускать после ~30 мин)

```bash
# MX
nslookup -type=MX glava.family
# ожидаем: mx.yandex.net

# SPF
nslookup -type=TXT glava.family
# ожидаем строку: v=spf1 include:_spf.yandex.net ~all

# DKIM
nslookup -type=TXT mail._domainkey.glava.family
# ожидаем: v=DKIM1; k=rsa; p=...

# DMARC
nslookup -type=TXT _dmarc.glava.family
# ожидаем: v=DMARC1; p=none; ...
```

Онлайн-проверка всего сразу:
https://mxtoolbox.com/SuperTool.aspx → ввести `glava.family` → Email Health
