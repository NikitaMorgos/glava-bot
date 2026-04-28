#!/bin/bash
# GLAVA ops.sh — автономные операции агента
# Использование: bash /opt/glava/ops.sh <команда>

set -a
source /opt/glava/.env 2>/dev/null
set +a

N8N_KEY=${N8N_API_KEY}
N8N_URL=http://localhost:5678

CMD=$1

case $CMD in
  logs-admin)
    journalctl -u glava-admin -n ${2:-100} --no-pager
    ;;
  logs-bot)
    journalctl -u glava -n ${2:-100} --no-pager
    ;;
  logs-n8n)
    docker logs n8n --tail=${2:-100} 2>&1
    ;;
  status)
    systemctl status glava glava-admin --no-pager
    ;;
  health)
    echo '=== Bot service ==='
    systemctl is-active glava && echo 'OK' || echo 'FAILED'
    echo '=== Admin service ==='
    systemctl is-active glava-admin && echo 'OK' || echo 'FAILED'
    echo '=== Admin HTTP ==='
    curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://localhost:5001/api/health
    echo '=== N8N ==='
    curl -s -o /dev/null -w 'HTTP %{http_code}\n' -H "X-N8N-API-KEY: $N8N_KEY" $N8N_URL/api/v1/workflows
    echo '=== N8N docker ==='
    docker ps | grep n8n | awk '{print $NF, $7}'
    ;;
  deploy)
    cd /opt/glava
    git stash 2>/dev/null || true
    git pull
    sudo systemctl restart glava-admin glava
    sleep 3
    bash /opt/glava/ops.sh health
    ;;
  restart)
    sudo systemctl restart glava-admin glava
    sleep 2
    bash /opt/glava/ops.sh health
    ;;
  seed-prompts)
    cd /opt/glava
    source .venv/bin/activate
    python scripts/_seed_prompts_v10.py && python scripts/_seed_prompts_v11.py
    ;;
  n8n-status)
    docker ps | grep n8n
    ;;
  n8n-workflows)
    curl -s -H "X-N8N-API-KEY: $N8N_KEY" $N8N_URL/api/v1/workflows | python3 -c "
import json,sys
data=json.load(sys.stdin)
for w in data.get('data',[]):
    print(f\"{w['id']:5} | {'ACTIVE' if w['active'] else 'off   '} | {w['name']}\")
"
    ;;
  n8n-executions)
    LIMIT=${2:-10}
    curl -s -H "X-N8N-API-KEY: $N8N_KEY" "$N8N_URL/api/v1/executions?limit=$LIMIT" | python3 -c "
import json,sys
data=json.load(sys.stdin)
for e in data.get('data',[]):
    print(f\"{e['id']:6} | {e.get('status','?'):10} | {e.get('startedAt','?')[:19]} | {e.get('workflowData',{}).get('name','?')}\")
"
    ;;
  n8n-execution)
    ID=${2:?'Usage: ops.sh n8n-execution <id>'}
    curl -s -H "X-N8N-API-KEY: $N8N_KEY" $N8N_URL/api/v1/executions/$ID | python3 -m json.tool
    ;;
  db-check)
    cd /opt/glava && source .venv/bin/activate
    python3 -c "
import os, psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM agents_prompts')
print('Prompts:', cur.fetchone()[0])
cur.execute('SELECT COUNT(*) FROM book_versions')
print('Book versions:', cur.fetchone()[0])
conn.close()
"
    ;;
  *)
    echo 'GLAVA ops.sh — доступные команды:'
    echo '  health             — статус всех сервисов'
    echo '  logs-admin [N]     — логи Flask admin (N строк)'
    echo '  logs-bot [N]       — логи Telegram бота'
    echo '  logs-n8n [N]       — логи n8n docker'
    echo '  status             — systemctl status'
    echo '  deploy             — git pull + restart + health'
    echo '  restart            — restart services + health'
    echo '  n8n-workflows      — список воркфлоу n8n'
    echo '  n8n-executions [N] — последние N executions'
    echo '  n8n-execution <id> — детали execution'
    echo '  db-check           — проверка БД'
    echo '  seed-prompts       — обновить промпты в БД'
    ;;
esac
