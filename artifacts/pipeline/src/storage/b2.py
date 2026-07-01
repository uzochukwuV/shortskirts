import boto3
import os
import io
import uuid
import httpx
from botocore.config import Config
from typing import Optional


def _env(key: str) -> str:
    return os.environ[key].strip()


def get_b2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{_env('B2_ENDPOINT_URL')}",
        aws_access_key_id=_env("B2_KEY_ID"),
        aws_secret_access_key=_env("B2_APPLICATION_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="us-east-005",
    )


BUCKET = lambda: _env("B2_BUCKET_NAME")


def upload_bytes(data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
    client = get_b2_client()
    client.put_object(
        Bucket=BUCKET(),
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    endpoint = os.environ["B2_ENDPOINT_URL"]
    bucket = BUCKET()
    return f"https://{endpoint}/{bucket}/{key}"


def upload_file(local_path: str, key: str, content_type: str = "application/octet-stream") -> str:
    client = get_b2_client()
    with open(local_path, "rb") as f:
        client.put_object(
            Bucket=BUCKET(),
            Key=key,
            Body=f,
            ContentType=content_type,
        )
    endpoint = os.environ["B2_ENDPOINT_URL"]
    bucket = BUCKET()
    return f"https://{endpoint}/{bucket}/{key}"


async def download_url_to_bytes(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.get(url, follow_redirects=True)
        r.raise_for_status()
        return r.content


async def download_and_upload(url: str, key: str, content_type: str = "video/mp4") -> str:
    data = await download_url_to_bytes(url)
    return upload_bytes(data, key, content_type)


def get_presigned_url(key: str, expires: int = 3600) -> str:
    client = get_b2_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET(), "Key": key},
        ExpiresIn=expires,
    )


def build_key(story_id: str, *parts: str) -> str:
    return f"stories/{story_id}/" + "/".join(parts)
