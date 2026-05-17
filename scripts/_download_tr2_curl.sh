#!/bin/bash
cd /opt/glava
source .venv/bin/activate
set -a; source /opt/glava/.env; set +a

mkdir -p collab/audio

echo "Скачиваем TR2 с AssemblyAI через curl..."
curl -k -L \
  -H "authorization: ${ASSEMBLYAI_API_KEY}" \
  'https://cdn.assemblyai.com/upload/c5d729e3932e6ee76afd435a7146d75fcb52834e1b134ca5664e2cb00735221e/f8be8a5f-4073-444b-928c-829363b1da05' \
  -o collab/audio/02_karakulina_nikita_tatyana_telemost_20260403.ogg \
  --progress-bar

echo ""
ls -lh collab/audio/02_karakulina_nikita_tatyana_telemost_20260403.ogg

echo "Загружаем в S3..."
python3 - <<'PYEOF'
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
local = '/opt/glava/collab/audio/02_karakulina_nikita_tatyana_telemost_20260403.ogg'
key = 'collab/02_karakulina_nikita_tatyana_telemost_20260403.ogg'

s3.upload_file(local, bucket, key)
url = s3.generate_presigned_url(
    'get_object',
    Params={'Bucket': bucket, 'Key': key},
    ExpiresIn=86400,
)
print(f"Готово! Presigned URL (24ч):\n{url}")
PYEOF
