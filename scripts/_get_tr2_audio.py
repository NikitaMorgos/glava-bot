#!/usr/bin/env python3
"""Скачивает аудио TR2 (vm_id=8, Никита+Татьяна, 3 апреля 2026) из S3
и кладёт в collab/audio/02_karakulina_nikita_tatyana_interview_20260403.<ext>
"""
import os, sys
from pathlib import Path
import psycopg2
import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv('/opt/glava/.env')

ROOT = Path('/opt/glava')
OUT_DIR = ROOT / 'collab' / 'audio'
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 1. Получаем storage_key и мета из БД
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute("""
    SELECT id, storage_key, duration, created_at
    FROM voice_messages WHERE id = 8
""")
row = cur.fetchone()
conn.close()

if not row:
    sys.exit("voice_message id=8 не найден в БД")

vm_id, storage_key, duration, created_at = row
print(f"vm_id={vm_id}, duration={duration}s ({duration//60} мин), created={created_at}")
print(f"storage_key: {storage_key}")

# 2. Определяем расширение из storage_key
ext = Path(storage_key).suffix or '.ogg'
out_file = OUT_DIR / f'02_karakulina_nikita_tatyana_interview_20260403{ext}'

# 3. Скачиваем из S3
s3 = boto3.client(
    's3',
    endpoint_url=os.environ.get('S3_ENDPOINT_URL', 'https://s3.amazonaws.com'),
    aws_access_key_id=os.environ['S3_ACCESS_KEY'],
    aws_secret_access_key=os.environ['S3_SECRET_KEY'],
    region_name=os.environ.get('S3_REGION', 'ru-central1'),
    config=Config(signature_version='s3v4'),
)
bucket = os.environ['S3_BUCKET_NAME']

print(f"\nСкачиваем s3://{bucket}/{storage_key} → {out_file}")
s3.download_file(bucket, storage_key, str(out_file))

size_mb = out_file.stat().st_size / 1_048_576
print(f"Готово: {out_file} ({size_mb:.1f} МБ)")

# 4. Также выводим presigned URL (на 24 часа)
url = s3.generate_presigned_url(
    'get_object',
    Params={'Bucket': bucket, 'Key': storage_key},
    ExpiresIn=86400,
)
print(f"\nPresigned URL (24ч):\n{url}")
