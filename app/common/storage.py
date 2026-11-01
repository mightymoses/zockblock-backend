from functools import lru_cache
import boto3
from botocore.exceptions import ClientError
from app.config import get_settings

# uploads land here first and are only moved out once they're actually referenced -
# an R2 lifecycle rule deletes everything left under this prefix after a day
PENDING_PREFIX = "pending/"


class StorageObjectNotFoundError(Exception):
    """Raised when an operation's source object doesn't exist in the bucket."""


@lru_cache
def get_s3_client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )


def public_url_for_key(key: str) -> str:
    return f"{get_settings().r2_public_base_url}/{key}"


def key_from_public_url(url: str) -> str | None:
    """Inverse of public_url_for_key - None if the URL doesn't point into our bucket."""
    prefix = f"{get_settings().r2_public_base_url}/"
    if not get_settings().r2_public_base_url or not url.startswith(prefix):
        return None
    return url.removeprefix(prefix)


def generate_presigned_upload_url(key: str, content_type: str) -> tuple[str, str]:
    """Creates a short-lived, presigned PUT URL for a direct client upload to R2,
    plus the public URL the object will be reachable at once uploaded.

    Only signs the URL locally (no network call), safe to call from an async route.
    """
    settings = get_settings()
    upload_url = get_s3_client().generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.r2_bucket_name,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=settings.presigned_url_expiry_seconds,
    )
    return upload_url, public_url_for_key(key)


def copy_object(source_key: str, target_key: str) -> None:
    """Server-side copy within the bucket (S3 has no move - delete the source separately)."""
    bucket = get_settings().r2_bucket_name
    try:
        get_s3_client().copy_object(
            Bucket=bucket,
            Key=target_key,
            CopySource={"Bucket": bucket, "Key": source_key},
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
            raise StorageObjectNotFoundError(source_key) from exc
        raise


def delete_object(key: str) -> None:
    get_s3_client().delete_object(Bucket=get_settings().r2_bucket_name, Key=key)
