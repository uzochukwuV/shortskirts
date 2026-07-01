import boto3
import os
import httpx
from botocore.config import Config


def _env(key: str) -> str:
    return os.environ[key].strip()


def get_write_client():
    """Write key — used for all uploads and deletes."""
    return boto3.client(
        "s3",
        endpoint_url=f"https://{_env('B2_ENDPOINT_URL')}",
        aws_access_key_id=_env("B2_KEY_ID"),
        aws_secret_access_key=_env("B2_APPLICATION_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="us-east-005",
    )


def BUCKET() -> str:
    return _env("B2_BUCKET_NAME")


def public_url(key: str) -> str:
    """B2 native CDN URL — works when bucket is Public OR key has readFiles.
    Format: https://f005.backblazeb2.com/file/{bucket}/{key}
    To enable: in Backblaze dashboard set bucket to Public, or create a key
    with the 'readFiles' capability checked.
    """
    # Use B2 native CDN URL (not S3 endpoint) for better compatibility
    return f"https://f005.backblazeb2.com/file/{BUCKET()}/{key}"


def upload_bytes(data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
    get_write_client().put_object(
        Bucket=BUCKET(),
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return public_url(key)


def upload_file(local_path: str, key: str, content_type: str = "application/octet-stream") -> str:
    with open(local_path, "rb") as f:
        get_write_client().put_object(
            Bucket=BUCKET(),
            Key=key,
            Body=f,
            ContentType=content_type,
        )
    return public_url(key)


async def download_url_to_bytes(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.get(url, follow_redirects=True)
        r.raise_for_status()
        return r.content


async def download_and_upload(url: str, key: str, content_type: str = "video/mp4") -> str:
    data = await download_url_to_bytes(url)
    return upload_bytes(data, key, content_type)


def get_presigned_url(key: str, expires: int = 3600) -> str:
    """Returns the public CDN URL. Requires bucket to be Public or key to have readFiles."""
    return public_url(key)


def build_key(story_id: str, *parts: str) -> str:
    return f"stories/{story_id}/" + "/".join(parts)
