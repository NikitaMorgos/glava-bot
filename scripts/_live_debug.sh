#!/bin/bash
# Trigger webhook and capture n8n logs
echo "=== Triggering webhook ==="
curl -s -X POST http://localhost:5678/webhook/glava/phase-a \
  -H 'Content-Type: application/json' \
  -d '{"telegram_id":577528,"draft_id":8,"character_name":"Test","transcript":"тест","photo_count":5}' &

# Immediately start capturing logs
sleep 0.5
echo "=== N8N LOGS (last 5 seconds) ==="
docker logs 25366fba0871 --since 3s 2>&1 | grep -v 'trust proxy\|ERR_ERL\|DeprecationWarning\|Pruning\|ValidationError\|express-rate'

wait
