# Развёртывание glava.family

Лендинг glava.family + личный кабинет cabinet.glava.family на VPS 72.56.121.94.

## Чеклист

### 1. Домен glava.family

Убедись, что домен glava.family привязан к твоему аккаунту (nic.ru, reg.ru или другой регистратор).

### 2. DNS

В панели управления доменом создай **A-записи** (укажи IP своего VPS, например 72.56.121.94):

| Запись               | Тип | Значение     |
|----------------------|-----|--------------|
| glava.family         | A   | 72.56.121.94 |
| www.glava.family     | A   | 72.56.121.94 |
| cabinet.glava.family | A   | 72.56.121.94 |

Подожди 5–30 минут, пока DNS обновится. Проверь: `nslookup glava.family`.

### 3. Лендинг на сервере

```bash
# Создать каталог и скопировать файлы
sudo mkdir -p /var/www/glava.family
sudo cp -r /opt/glava/landing/* /var/www/glava.family/
sudo chown -R www-data:www-data /var/www/glava.family
```

### 4. Nginx

```bash
# Скопировать конфиги
sudo cp /opt/glava/deploy/nginx-glava.conf /etc/nginx/sites-available/glava
sudo cp /opt/glava/deploy/nginx-cabinet.conf /etc/nginx/sites-available/cabinet

# Убрать старый default (если был glava-cabinet)
sudo rm -f /etc/nginx/sites-enabled/glava-cabinet
sudo rm -f /etc/nginx/sites-enabled/default

# Включить glava и cabinet
sudo ln -sf /etc/nginx/sites-available/glava /etc/nginx/sites-enabled/
sudo ln -sf /etc/nginx/sites-available/cabinet /etc/nginx/sites-enabled/

# Проверить и перезагрузить
sudo nginx -t && sudo systemctl reload nginx
```

### 5. SSL (HTTPS)

```bash
# Установить certbot, если ещё нет
sudo apt install -y certbot python3-certbot-nginx

# Получить сертификаты
sudo certbot --nginx -d glava.family -d www.glava.family -d cabinet.glava.family --non-interactive
```

Certbot сам добавит SSL в конфиги nginx. После этого будет доступно:
- https://glava.family
- https://www.glava.family  
- https://cabinet.glava.family

### 6. CABINET_SECRET_KEY

В `.env` на сервере:

```bash
nano /opt/glava/.env
```

Добавь (если ещё нет):

```
CABINET_SECRET_KEY=случайная_строка_минимум_32_символа
TRUST_PROXY=1
```

Перезапуск кабинета:

```bash
sudo systemctl restart glava-cabinet
```

---

## Результат

| URL                      | Содержимое                         |
|--------------------------|------------------------------------|
| https://glava.family     | Лендинг + ссылка на кабинет        |
| https://cabinet.glava.family | Личный кабинет (вход по паролю) |
| https://t.me/glava_voice_bot | Бот (пароль для кабинета: /cabinet) |

---

## Обновление проекта

После изменений в коде (бот, тексты, пайплайны):

```bash
cd /opt/glava && git pull
sudo systemctl restart glava           # обязательно — бот читает код при старте
sudo systemctl restart glava-cabinet   # если менялся кабинет
```

Проверь что бот поднялся с новым кодом:
```bash
journalctl -u glava -n 20
systemctl status glava
```

После изменений только в `landing/`:

```bash
cd /opt/glava && git pull
sudo cp -r /opt/glava/landing/* /var/www/glava.family/
# бот перезапускать не нужно — он лендинг не обслуживает
```
