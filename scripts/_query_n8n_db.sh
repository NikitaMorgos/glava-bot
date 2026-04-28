#!/bin/sh
sqlite3 /data/n8n/.n8n/database.sqlite "SELECT id, status, stoppedAt, substr(data, 1, 500) FROM execution_entity WHERE id >= 64 ORDER BY id DESC LIMIT 5"
