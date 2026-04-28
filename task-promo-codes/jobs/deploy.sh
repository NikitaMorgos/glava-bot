#!/bin/bash
# Деплой промо-кодов на сервер
# Запуск: bash task-promo-codes/jobs/deploy.sh
# Предварительно: убедитесь, что файлы в локальной папке актуальны

SERVER=root@72.56.121.94
GLAVA=/opt/glava

echo "==> Деплой файлов промо-кодов..."
scp db_promo.py                                    $SERVER:$GLAVA/db_promo.py
scp db_draft.py                                    $SERVER:$GLAVA/db_draft.py
scp config.py                                      $SERVER:$GLAVA/config.py
scp main.py                                        $SERVER:$GLAVA/main.py
scp prepay/keyboards.py                            $SERVER:$GLAVA/prepay/keyboards.py
scp prepay/messages.py                             $SERVER:$GLAVA/prepay/messages.py
scp admin/blueprints/lena.py                       $SERVER:$GLAVA/admin/blueprints/lena.py
scp admin/db_admin.py                              $SERVER:$GLAVA/admin/db_admin.py
scp admin/templates/base.html                      $SERVER:$GLAVA/admin/templates/base.html
scp admin/templates/lena/promos.html               $SERVER:$GLAVA/admin/templates/lena/promos.html
scp admin/templates/lena/promo_new.html            $SERVER:$GLAVA/admin/templates/lena/promo_new.html
scp admin/templates/lena/promo_usages.html         $SERVER:$GLAVA/admin/templates/lena/promo_usages.html

echo "==> Перезапуск сервисов..."
ssh $SERVER "systemctl restart glava.service glava-admin.service"
sleep 3
ssh $SERVER "systemctl is-active glava.service glava-admin.service"
echo "==> Готово"
