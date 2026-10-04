from __future__ import annotations

import os
import shutil
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Protocol
from uuid import uuid4


class ObjectStorage(Protocol):
    def put(
        self, key: str, source: BinaryIO, content_type: str = "application/octet-stream"
    ) -> None: ...
    def download(self, key: str, destination: Path) -> None: ...
    def read(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...
    def delete(self, key: str) -> None: ...
    def delete_prefix(self, prefix: str) -> None: ...


def check_key(key: str) -> str:
    path = PurePosixPath(key)
    if not key or path.is_absolute() or ".." in path.parts or "\\" in key:
        raise ValueError("Referencia de almacenamiento inválida.")
    return key


class LocalStorage:
    """Atomic local adapter for development; replicas need shared durable storage."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, key: str) -> Path:
        path = (self.root / check_key(key)).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Referencia de almacenamiento inválida.")
        return path

    def put(
        self, key: str, source: BinaryIO, content_type: str = "application/octet-stream"
    ) -> None:
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.{uuid4()}.tmp")
        try:
            with temporary.open("wb") as stream:
                shutil.copyfileobj(source, stream)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)

    def download(self, key: str, destination: Path) -> None:
        shutil.copyfile(self.path(key), destination)

    def read(self, key: str) -> bytes:
        return self.path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self.path(key).is_file()

    def delete(self, key: str) -> None:
        self.path(key).unlink(missing_ok=True)

    def delete_prefix(self, prefix: str) -> None:
        directory = self.path(prefix)
        if directory == self.root:
            raise ValueError("No se puede eliminar la raíz del almacenamiento.")
        if directory.is_dir():
            shutil.rmtree(directory)


class S3Storage:
    def __init__(self, bucket: str, endpoint: str | None = None):
        import boto3
        from botocore.config import Config

        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            config=Config(
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=10,
                read_timeout=60,
            ),
        )

    def put(
        self, key: str, source: BinaryIO, content_type: str = "application/octet-stream"
    ) -> None:
        self.client.upload_fileobj(
            source, self.bucket, check_key(key), ExtraArgs={"ContentType": content_type}
        )

    def download(self, key: str, destination: Path) -> None:
        self.client.download_file(self.bucket, check_key(key), str(destination))

    def read(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=check_key(key))
        try:
            return response["Body"].read()
        finally:
            response["Body"].close()

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.client.head_object(Bucket=self.bucket, Key=check_key(key))
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=check_key(key))

    def delete_prefix(self, prefix: str) -> None:
        key_prefix = check_key(prefix).rstrip("/") + "/"
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=key_prefix):
            objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
            if objects:
                response = self.client.delete_objects(
                    Bucket=self.bucket,
                    Delete={"Objects": objects, "Quiet": True},
                )
                if response.get("Errors"):
                    raise OSError("No se pudieron eliminar todos los objetos del prefijo.")


def from_env() -> ObjectStorage:
    driver = os.environ.get("STORAGE_DRIVER", "s3")
    if driver == "local":
        return LocalStorage(Path(os.environ.get("STORAGE_LOCAL_ROOT", ".runtime/objects")))
    if driver != "s3":
        raise ValueError("STORAGE_DRIVER debe ser s3 o local.")
    return S3Storage(os.environ["S3_BUCKET"], os.environ.get("S3_ENDPOINT_URL"))
