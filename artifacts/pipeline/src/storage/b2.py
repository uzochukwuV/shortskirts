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


def get_read_client():
    """Read key — used for download URLs that third-party model providers fetch."""
    key_id = os.environ.get("B2_READ_KEY_ID") or os.environ.get("B2_KEY_ID")
    app_key = os.environ.get("B2_READ_APPLICATION_KEY") or os.environ.get("B2_APPLICATION_KEY")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{_env('B2_ENDPOINT_URL')}",
        aws_access_key_id=key_id,
        aws_secret_access_key=app_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-005",
    )


def BUCKET() -> str:
    return _env("B2_BUCKET_NAME")


def public_url(key: str) -> str:
    """Return a signed GET URL for a private B2 object.

    The bucket in this workspace is not public, so downstream services like
    AIML/DashScope must receive a fetchable presigned URL rather than a bare
    bucket path.
    """
    return get_read_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET(), "Key": key},
        ExpiresIn=7 * 24 * 60 * 60,
    )


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
    return get_read_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET(), "Key": key},
        ExpiresIn=expires,
    )


def build_key(story_id: str, *parts: str) -> str:
    return f"stories/{story_id}/" + "/".join(parts)
