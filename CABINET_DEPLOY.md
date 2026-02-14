# Развёртывание личного кабинета (cabinet.glava.family)

## 1. Добавить в .env на VPS

```
CABINET_SECRET_KEY=сгенерируй_случайную_строку_32_символа
TRUST_PROXY=1
```

## 2. Установить gunicorn (если ещё не установлен)

```bash
cd /opt/glava
source venv/bin/activate
pip install gunicorn
```

## 3. systemd-сервис

```bash
cp deploy/glava-cabinet.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable glava-cabinet
systemctl start glava-cabinet
systemctl status glava-cabinet
```

Кабинет будет слушать `127.0.0.1:5000` (только localhost).

## 4. Nginx + SSL (для cabinet.glava.family)

Установи nginx и certbot, добавь A-запись `cabinet.glava.family` → IP_VPS.

Пример конфига nginx `/etc/nginx/sites-available/cabinet`:

```nginx
server {
    listen 80;
    server_name cabinet.glava.family;
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/cabinet /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
certbot --nginx -d cabinet.glava.family
```

## 5. PDF-документы

Чтобы в кабинете отображались ссылки на PDF (one-pager и др.):

1. Создай PDF (например, через `scripts/add_logo_to_pdf.py` для one-pager)
2. Положи в `cabinet/static/pdfs/`:
   - `one-pager.pdf` — краткое описание Glava
3. Список документов настраивается в `cabinet/app.py` → `PDF_DOCUMENTS`

## 6. Пользователи

1. Пользователь пишет боту: `/cabinet` → вводит пароль
2. Заходит на cabinet.glava.family с логином (@username или telegram_id) и паролем
