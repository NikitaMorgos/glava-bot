"""
Работа с S3-совместимым облачным хранилищем.
Загрузка файлов и получение ссылок для скачивания.
"""

import os
import uuid
from pathlib import Path

import boto3
from botocore.config import Config

import config


def get_s3_client():
    """
    Создаёт клиент для S3-совместимого хранилища.
    Подходит для: AWS S3, MinIO, Yandex Object Storage и др.
    """
    return boto3.client(
        "s3",
        endpoint_url=config.S3_ENDPOINT_URL,
        aws_access_key_id=config.S3_ACCESS_KEY,
        aws_secret_access_key=config.S3_SECRET_KEY,
        region_name=config.S3_REGION,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket_exists():
    """
    Создаёт бакет, если его ещё нет.
    Вызывать при старте приложения (опционально).
    """
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=config.S3_BUCKET_NAME)
    except client.exceptions.ClientError:
        client.create_bucket(Bucket=config.S3_BUCKET_NAME)


def upload_file(file_path: str, user_id: int) -> str:
    """
    Загружает файл в облако.
    file_path — путь к локальному файлу,
    user_id — ID пользователя (для организации папок в хранилище).

    Возвращает storage_key — ключ/путь файла в облаке.
    """
    client = get_s3_client()
    ext = Path(file_path).suffix or ".ogg"
    storage_key = f"users/{user_id}/{uuid.uuid4().hex}{ext}"

    client.upload_file(
        Filename=file_path,
        Bucket=config.S3_BUCKET_NAME,
        Key=storage_key,
    )
    return storage_key


def download_file(storage_key: str, local_path: str) -> None:
    """
    Скачивает файл из облака в локальную папку.
    Сначала во временный файл вне папки проекта (избегаем WinError 32 при Dropbox-синке).
    """
    import shutil
    import tempfile

    client = get_s3_client()
    path = Path(local_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(suffix=path.suffix, dir=tempfile.gettempdir())
    try:
        os.close(fd)
        client.download_file(
            Bucket=config.S3_BUCKET_NAME,
            Key=storage_key,
            Filename=tmp_path,
        )
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass
        shutil.copy2(tmp_path, local_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def upload_file_to_key(local_path: str, storage_key: str) -> None:
    """Загружает локальный файл в облако по заданному ключу."""
    client = get_s3_client()
    client.upload_file(
        Filename=local_path,
        Bucket=config.S3_BUCKET_NAME,
        Key=storage_key,
    )


def delete_object(storage_key: str) -> None:
    """Удаляет объект из хранилища."""
    client = get_s3_client()
    client.delete_object(Bucket=config.S3_BUCKET_NAME, Key=storage_key)


def get_presigned_download_url(storage_key: str, expires_in: int = 3600) -> str:
    """
    Создаёт временную ссылку для скачивания файла.
    Ссылка действует expires_in секунд (по умолчанию 1 час).
    """
    client = get_s3_client()
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": config.S3_BUCKET_NAME, "Key": storage_key},
        ExpiresIn=expires_in,
    )
    return url
