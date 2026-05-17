#!/usr/bin/env python3
import os, requests, boto3, urllib3
from pathlib import Path
from botocore.config import Config
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')

urllib3.disable_warnings()

api_key = os.environ['ASSEMBLYAI_API_KEY']
headers = {'authorization': api_key}

# Получаем свежий audio_url
print("Получаем свежий audio_url с AssemblyAI...")
r = requests.get(
    'https://api.assemblyai.com/v2/transcript/dec7960b-c4d0-4bad-912e-013a6029b799',
    headers=headers, verify=False, timeout=30,
)
t = r.json()
audio_url = t.get('audio_url', '')
duration = t.get('audio_duration', 0)
print(f"Duration: {duration}s = {duration//60}мин")
print(f"Audio URL: {audio_url[:100]}")

# Скачиваем аудио
print("\nСкачиваем аудио...")
resp = requests.get(audio_url, headers=headers, stream=True, timeout=180, verify=False)
print(f"HTTP status: {resp.status_code}")
resp.raise_for_status()

out = Path('/opt/glava/collab/audio/02_karakulina_tr2_telemost_20260403.ogg')
out.parent.mkdir(parents=True, exist_ok=True)
downloaded = 0
with open(out, 'wb') as f:
    for chunk in resp.iter_content(chunk_size=65536):
        f.write(chunk)
        downloaded += len(chunk)
        if downloaded % (5 * 1024 * 1024) < 65536:
            print(f"  {downloaded // 1024 // 1024} МБ...")

size_mb = out.stat().st_size / 1_048_576
print(f"Сохранено: {out} ({size_mb:.1f} МБ)")

# Заливаем в S3
print("\nЗагружаем в S3...")
s3 = boto3.client(
    's3',
    endpoint_url=os.environ.get('S3_ENDPOINT_URL'),
    aws_access_key_id=os.environ['S3_ACCESS_KEY'],
    aws_secret_access_key=os.environ['S3_SECRET_KEY'],
    region_name=os.environ.get('S3_REGION', 'ru-central1'),
    config=Config(signature_version='s3v4'),
)
bucket = os.environ['S3_BUCKET_NAME']
key = 'collab/02_karakulina_tr2_telemost_20260403.ogg'
s3.upload_file(str(out), bucket, key)

url = s3.generate_presigned_url(
    'get_object',
    Params={'Bucket': bucket, 'Key': key},
    ExpiresIn=86400,
)
print(f"\nPresigned URL (24ч):\n{url}")
