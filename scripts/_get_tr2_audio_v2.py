#!/usr/bin/env python3
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
key = 'users/2/fba0781bc23747499dfd474cb2cab5b5.mp3'

url = s3.generate_presigned_url(
    'get_object',
    Params={'Bucket': bucket, 'Key': key},
    ExpiresIn=86400,
)
print(url)
