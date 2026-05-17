#!/usr/bin/env python3
"""Генерирует presigned URL для кандидатов TR2"""
import os, boto3
from botocore.config import Config
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')

s3 = boto3.client(
    's3',
    endpoint_url=os.environ.get('S3_ENDPOINT_URL'),
    aws_access_key_id=os.environ['S3_ACCESS_KEY'],
    aws_secret_access_key=os.environ['S3_SECRET_KEY'],
    region_name=os.environ.get('S3_REGION', 'ru-central1'),
    config=Config(signature_version='s3v4'),
)
bucket = os.environ['S3_BUCKET_NAME']

candidates = {
    'vm_id=6 (user=3, 39мин, 13 фев)': 'users/3/03b957f1911a41bd999ccce41f0dc044.mp3',
}

for name, key in candidates.items():
    url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': key},
        ExpiresIn=86400,
    )
    print(f"\n{name}:\n{url}")

# pipelines/interview_input/voice_6.mp3 — отдаём напрямую
import subprocess
result = subprocess.run(
    ['ls', '-lh', '/opt/glava/pipelines/interview_input/voice_6.mp3'],
    capture_output=True, text=True
)
print(f"\npipelines/interview_input/voice_6.mp3:\n{result.stdout.strip()}")

# Загружаем voice_6.mp3 в S3 под temp ключом и даём ссылку
local_path = '/opt/glava/pipelines/interview_input/voice_6.mp3'
if os.path.exists(local_path):
    temp_key = 'temp/voice_6_karakulina_interview.mp3'
    s3.upload_file(local_path, bucket, temp_key)
    url2 = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': temp_key},
        ExpiresIn=86400,
    )
    print(f"\npipelines/voice_6.mp3 (загружен в S3 temp):\n{url2}")
