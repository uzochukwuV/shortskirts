import boto3
import os
import httpx
from botocore.config import Config


def _env(key: str) -> str:
    return os.environ[key].strip()


def _make_client(key_id: str, app_key: str):
    return boto3.client(
        "s3",
        endpoint_url=f"https://{_env('B2_ENDPOINT_URL')}",
        aws_access_key_id=key_id,
        aws_secret_access_key=app_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-005",
    )


def get_write_client():
    """Write-only key — used for uploads and deletes."""
    return _make_client(_env("B2_KEY_ID"), _env("B2_APPLICATION_KEY"))


def get_read_client():
    """Read-only key — used for downloads and presigned URLs.
    Falls back to the write key if no separate read key is configured."""
    read_key_id = os.environ.get("B2_READ_KEY_ID", "").strip()
    read_app_key = os.environ.get("B2_READ_APPLICATION_KEY", "").strip()
    if read_key_id and read_app_key:
        return _make_client(read_key_id, read_app_key)
    return get_write_client()


BUCKET = lambda: _env("B2_BUCKET_NAME")


def upload_bytes(data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
    get_write_client().put_object(
        Bucket=BUCKET(),
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return f"https://{_env('B2_ENDPOINT_URL')}/{BUCKET()}/{key}"


def upload_file(local_path: str, key: str, content_type: str = "application/octet-stream") -> str:
    with open(local_path, "rb") as f:
        get_write_client().put_object(
            Bucket=BUCKET(),
            Key=key,
            Body=f,
            ContentType=content_type,
        )
    return f"https://{_env('B2_ENDPOINT_URL')}/{BUCKET()}/{key}"


async def download_url_to_bytes(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.get(url, follow_redirects=True)
        r.raise_for_status()
        return r.content


async def download_and_upload(url: str, key: str, content_type: str = "video/mp4") -> str:
    data = await download_url_to_bytes(url)
    return upload_bytes(data, key, content_type)


def get_presigned_url(key: str, expires: int = 3600) -> str:
    return get_read_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET(), "Key": key},
        ExpiresIn=expires,
    )


def build_key(story_id: str, *parts: str) -> str:
    return f"stories/{story_id}/" + "/".join(parts)
