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
print(f"Bucket: {bucket}")

paginator = s3.get_paginator('list_objects_v2')
for page in paginator.paginate(Bucket=bucket):
    for obj in page.get('Contents', []):
        key = obj['Key']
        size_mb = obj['Size'] / 1_048_576
        modified = str(obj['LastModified'])[:10]
        print(f"{size_mb:6.1f} MB  {modified}  {key}")
