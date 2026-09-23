from __future__ import annotations

import asyncio
import mimetypes
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol


from cloud.config import cloud_settings


DEFAULT_STORAGE_PREFIX = "uploads"
DEFAULT_FILENAME = "file.bin"
DEFAULT_CONTENT_TYPE = "application/octet-stream"
DEFAULT_PRESIGN_EXPIRES_SECONDS = 900
MIN_PRESIGN_EXPIRES_SECONDS = 60
MAX_PRESIGN_EXPIRES_SECONDS = 3600

MAX_FILENAME_LENGTH = 160
MAX_PREFIX_LENGTH = 120
MAX_CONTENT_TYPE_LENGTH = 128


class ObjectStorageError(RuntimeError):
    """
    对象存储基础异常。

    所有对象存储相关的可预期异常都应该继承该异常，
    这样 API 层可以根据 stage 统一生成错误响应。
    """

    stage = "object_storage"


class ObjectStorageValidationError(ObjectStorageError):
    """
    对象存储输入参数校验失败。
    """

    stage = "object_storage_validation"


class ObjectStorageUnsupportedError(ObjectStorageError):
    """
    当前对象存储实现不支持目标操作。
    """

    stage = "object_storage_unsupported"


class ObjectStorageConfigError(ObjectStorageError):
    """
    对象存储配置不完整或不合法。
    """

    stage = "object_storage_config"


@dataclass(frozen=True)
class StoredObject:
    """
    文件写入对象存储后的标准结果。
    """

    key: str
    url: str
    size: int
    content_type: str


class ObjectStore(Protocol):
    """
    对象存储适配器协议。

    Local、S3、COS 都必须实现同一组异步方法，
    上层业务不需要感知具体存储提供商。
    """

    async def put_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredObject:
        ...

    async def presigned_put_url(
        self,
        key: str,
        content_type: str,
        expires_seconds: int,
    ) -> str:
        ...

    async def presigned_get_url(
        self,
        key: str,
        expires_seconds: int,
    ) -> str:
        ...

    def describe(self) -> dict[str, Any]:
        """返回与 provider 无关的身份信息，供 readiness/diagnostics 展示。"""
        ...


def normalize_storage_prefix(
    value: str | None,
    *,
    default: str = DEFAULT_STORAGE_PREFIX,
) -> str:
    """
    规范化对象存储目录前缀。

    处理规则：

    1. 去除首尾空白和斜杠。
    2. 统一反斜杠为正斜杠。
    3. 保留字母、数字、下划线、短横线和目录分隔符。
    4. 删除空目录片段和当前目录片段。
    5. 禁止父级目录片段，避免路径穿越。
    6. 空值时回退到默认前缀。
    """

    raw = (value or "").strip().replace("\\", "/")

    if not raw:
        raw = default

    parts: list[str] = []

    for part in raw.split("/"):
        part = part.strip()

        if not part or part == ".":
            continue

        if part == "..":
            raise ObjectStorageValidationError(
                "storage prefix must not contain parent directory segments"
            )

        safe_part = re.sub(r"[^a-zA-Z0-9_-]+", "-", part).strip("-_")

        if safe_part:
            parts.append(safe_part)

    normalized = "/".join(parts)

    if not normalized:
        normalized = default.strip().strip("/")

    if len(normalized) > MAX_PREFIX_LENGTH:
        normalized = normalized[:MAX_PREFIX_LENGTH].rstrip("/")

    return normalized or DEFAULT_STORAGE_PREFIX


def normalize_filename(
    value: str | None,
    *,
    default: str = DEFAULT_FILENAME,
) -> str:
    """
    规范化上传文件名。

    只保留文件名，不允许携带目录结构。
    这样可以避免通过 filename 构造任意本地路径。
    """

    raw = (value or "").strip().replace("\\", "/")

    if not raw:
        raw = default

    filename = Path(raw).name

    if filename in {"", ".", ".."}:
        filename = default

    if ".." in filename:
        filename = filename.replace("..", "_")

    filename = re.sub(r"[^a-zA-Z0-9._-]+", "_", filename)
    filename = filename.strip("._-")

    if not filename:
        filename = default

    return filename[:MAX_FILENAME_LENGTH]


def normalize_content_type(value: str | None) -> str:
    """
    规范化 MIME Content-Type。

    Content-Type 主要用于：

    - S3/COS put_object。
    - 预签名上传时的签名参数。
    - 客户端后续下载或播放时的响应头判断。
    """

    content_type = (value or "").strip().lower()

    if not content_type:
        return DEFAULT_CONTENT_TYPE

    if len(content_type) > MAX_CONTENT_TYPE_LENGTH:
        raise ObjectStorageValidationError("content_type is too long")

    if not re.fullmatch(
        r"[a-z0-9][a-z0-9!#$&^_.+-]*/[a-z0-9][a-z0-9!#$&^_.+-]*(?:\s*;\s*.+)?",
        content_type,
    ):
        raise ObjectStorageValidationError("content_type is invalid")

    return content_type


def normalize_expires_seconds(
    value: int | None,
    *,
    default: int = DEFAULT_PRESIGN_EXPIRES_SECONDS,
    minimum: int = MIN_PRESIGN_EXPIRES_SECONDS,
    maximum: int = MAX_PRESIGN_EXPIRES_SECONDS,
) -> int:
    """
    规范化预签名 URL 有效期。

    API 层已经通过 Pydantic 做了一次校验，
    这里仍然保留边界保护，防止其它内部调用绕过 API 直接传入异常值。
    """

    if value is None:
        value = default

    try:
        expires_seconds = int(value)
    except (TypeError, ValueError) as exc:
        raise ObjectStorageValidationError(
            "expires_seconds must be an integer"
        ) from exc

    return max(minimum, min(maximum, expires_seconds))


def build_object_key(
    prefix: str | None,
    filename: str | None,
) -> str:
    """
    构建统一对象 key。

    示例：

    uploads/2026/09/17/103015-avatar.png

    时间目录可以降低单目录文件数量，
    同时保留上传时间，便于排查和生命周期清理。
    """

    now = datetime.now(timezone.utc)
    safe_prefix = normalize_storage_prefix(prefix)
    safe_filename = normalize_filename(filename)

    return (
        f"{safe_prefix}/"
        f"{now:%Y/%m/%d}/"
        f"{now:%H%M%S}-{safe_filename}"
    )


def guess_content_type(
    filename: str | None,
    fallback: str = DEFAULT_CONTENT_TYPE,
) -> str:
    """
    根据文件名猜测 MIME 类型。

    无法识别时使用 application/octet-stream。
    """

    if not filename:
        return fallback

    return mimetypes.guess_type(filename)[0] or fallback


def stored_object_payload(stored: StoredObject) -> dict[str, Any]:
    """
    将内部 StoredObject 转换为 API 对外响应结构。
    """

    return {
        "key": stored.key,
        "url": stored.url,
        "size": stored.size,
        "content_type": stored.content_type,
        "provider": cloud_settings.storage_provider.strip().lower(),
    }


class LocalObjectStore:
    """
    本地对象存储实现。

    适用于：

    - 本地开发。
    - Mock 模式。
    - CI 测试。
    - 没有云存储依赖的单机部署。

    Local 存储可以生成普通访问 URL，
    但不能生成真正具有签名能力的预签名上传 URL。
    """

    def __init__(self, root: str, public_base_url: str) -> None:
        self.root = Path(root)
        self.public_base_url = public_base_url.rstrip("/")

    def describe(self) -> dict[str, Any]:
        url_prefix = f"{self.public_base_url}/cloud-files" if self.public_base_url else "/cloud-files"

        return {
            "provider": "local",
            "root": str(self.root),
            "key_prefix": "",
            "url_prefix": url_prefix,
            "public_base_url": self.public_base_url,
            "presigned_supported": False,
        }

    def _resolve_key(self, key: str) -> Path:
        """
        将对象 key 解析到 root 目录内。

        即使调用方没有经过 build_object_key，
        这里也会再次阻止绝对路径和路径穿越。
        """

        normalized_key = key.replace("\\", "/").strip("/")

        if not normalized_key or normalized_key in {".", ".."}:
            raise ObjectStorageValidationError("object key is empty")

        if ".." in Path(normalized_key).parts:
            raise ObjectStorageValidationError(
                "object key must not contain parent directory segments"
            )

        target = (self.root / normalized_key).resolve()
        root = self.root.resolve()

        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ObjectStorageValidationError(
                "object key escapes local storage root"
            ) from exc

        return target

    def _public_url(self, key: str) -> str:
        key = key.replace("\\", "/").strip("/")

        if self.public_base_url:
            return f"{self.public_base_url}/cloud-files/{key}"

        return f"/cloud-files/{key}"

    async def put_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredObject:
        safe_content_type = normalize_content_type(content_type)
        path = self._resolve_key(key)

        path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, data)

        return StoredObject(
            key=key.replace("\\", "/").strip("/"),
            url=self._public_url(key),
            size=len(data),
            content_type=safe_content_type,
        )

    async def presigned_put_url(
        self,
        key: str,
        content_type: str,
        expires_seconds: int,
    ) -> str:
        raise ObjectStorageUnsupportedError(
            "local storage does not support presigned upload url"
        )

    async def presigned_get_url(
        self,
        key: str,
        expires_seconds: int,
    ) -> str:
        self._resolve_key(key)
        normalize_expires_seconds(expires_seconds)
        return self._public_url(key)


class S3ObjectStore:
    """
    S3/COS 对象存储实现。

    腾讯云 COS 可以通过 S3 兼容接口接入，
    因此这里统一使用 boto3 的 S3 API。
    """

    def __init__(self) -> None:
        if not cloud_settings.s3_bucket.strip():
            raise ObjectStorageConfigError(
                "S3_BUCKET is required when STORAGE_PROVIDER is s3 or cos"
            )

        import boto3

        self.bucket = cloud_settings.s3_bucket.strip()
        self.public_base_url = cloud_settings.s3_public_base_url.rstrip("/")

        self.client = boto3.client(
            "s3",
            endpoint_url=cloud_settings.s3_endpoint_url or None,
            region_name=cloud_settings.s3_region,
            aws_access_key_id=cloud_settings.s3_access_key_id,
            aws_secret_access_key=cloud_settings.s3_secret_access_key,
        )

    def describe(self) -> dict[str, Any]:
        # S3 与 COS 共用同一实现，这里如实回显当前配置的 provider 名称。
        return {
            "provider": cloud_settings.storage_provider.strip().lower(),
            "bucket": self.bucket,
            "endpoint_url": cloud_settings.s3_endpoint_url,
            "region": cloud_settings.s3_region,
            "key_prefix": "",
            "url_prefix": self.public_base_url or "presigned",
            "public_base_url": self.public_base_url,
            "presigned_supported": True,
        }

    async def put_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredObject:
        safe_content_type = normalize_content_type(content_type)

        await asyncio.to_thread(
            self.client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=safe_content_type,
        )

        if self.public_base_url:
            url = f"{self.public_base_url}/{key}"
        else:
            url = await self.presigned_get_url(key, 3600)

        return StoredObject(
            key=key,
            url=url,
            size=len(data),
            content_type=safe_content_type,
        )

    async def presigned_put_url(
        self,
        key: str,
        content_type: str,
        expires_seconds: int,
    ) -> str:
        safe_content_type = normalize_content_type(content_type)
        safe_expires_seconds = normalize_expires_seconds(expires_seconds)

        return await asyncio.to_thread(
            self.client.generate_presigned_url,
            "put_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ContentType": safe_content_type,
            },
            ExpiresIn=safe_expires_seconds,
        )

    async def presigned_get_url(
        self,
        key: str,
        expires_seconds: int,
    ) -> str:
        safe_expires_seconds = normalize_expires_seconds(expires_seconds)

        return await asyncio.to_thread(
            self.client.generate_presigned_url,
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
            },
            ExpiresIn=safe_expires_seconds,
        )


_object_store: ObjectStore | None = None


def get_object_store() -> ObjectStore:
    """
    获取当前配置对应的对象存储实例。

    生产运行期间复用同一实例，
    避免每个请求重复初始化 boto3 client。
    """

    global _object_store

    if _object_store is not None:
        return _object_store

    provider = cloud_settings.storage_provider.strip().lower()

    if provider in {"s3", "cos"}:
        _object_store = S3ObjectStore()
    elif provider == "local":
        _object_store = LocalObjectStore(
            root=cloud_settings.local_storage_root,
            public_base_url=cloud_settings.api_public_base_url,
        )
    else:
        raise ObjectStorageConfigError(
            f"unsupported storage provider: {cloud_settings.storage_provider}"
        )

    return _object_store


def reset_object_store_for_tests() -> None:
    """
    仅供测试使用。

    测试修改 STORAGE_PROVIDER、LOCAL_STORAGE_ROOT 或相关配置后，
    必须清理缓存，否则后续测试仍会继续使用旧实例。
    """

    global _object_store
    _object_store = None