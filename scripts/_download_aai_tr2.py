#!/usr/bin/env python3
"""Скачивает аудио TR2 с AssemblyAI и кладёт в S3 + collab/audio/"""
import os, requests, boto3
from pathlib import Path
from botocore.config import Config
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')

api_key = os.environ['ASSEMBLYAI_API_KEY']
headers = {'authorization': api_key}

audio_url = 'https://cdn.assemblyai.com/upload/c5d729e3932e6ee76afd435a7146d75fcb52834e1b134ca5664e2cb00735221e/f8be8a5f-4073-444b-928c-829363b1da05'

# Скачиваем с авторизацией
print("Скачиваем с AssemblyAI...")
resp = requests.get(audio_url, headers=headers, stream=True, timeout=120)
resp.raise_for_status()

local_path = Path('/opt/glava/collab/audio/02_karakulina_nikita_tatyana_telemost_20260403.ogg')
local_path.parent.mkdir(parents=True, exist_ok=True)

with open(local_path, 'wb') as f:
    for chunk in resp.iter_content(chunk_size=65536):
        f.write(chunk)

size_mb = local_path.stat().st_size / 1_048_576
print(f"Сохранено: {local_path} ({size_mb:.1f} МБ)")

# Заливаем в S3
s3 = boto3.client(
    's3',
    endpoint_url=os.environ.get('S3_ENDPOINT_URL'),
    aws_access_key_id=os.environ['S3_ACCESS_KEY'],
    aws_secret_access_key=os.environ['S3_SECRET_KEY'],
    region_name=os.environ.get('S3_REGION', 'ru-central1'),
    config=Config(signature_version='s3v4'),
)
bucket = os.environ['S3_BUCKET_NAME']
s3_key = 'collab/02_karakulina_nikita_tatyana_telemost_20260403.ogg'

print(f"Загружаем в S3 s3://{bucket}/{s3_key} ...")
s3.upload_file(str(local_path), bucket, s3_key)

url = s3.generate_presigned_url(
    'get_object',
    Params={'Bucket': bucket, 'Key': s3_key},
    ExpiresIn=86400,
)
print(f"\nPresigned URL (24ч):\n{url}")
