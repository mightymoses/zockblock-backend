from functools import lru_cache
import boto3
from app.config import get_settings


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
    public_url = f"{settings.r2_public_base_url}/{key}"
    return upload_url, public_url
