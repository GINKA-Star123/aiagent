from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

from aiagent.common.log_safety import sanitize_text
from apps.api.request_context import (
    get_request_id,
    get_request_method,
    get_request_path,
)


_STANDARD_RECORD_FIELDS = set(
    logging.LogRecord(
        name="",
        level=0,
        pathname="",
        lineno=0,
        msg="",
        args=(),
        exc_info=None,
    ).__dict__.keys()
)


def _utc_timestamp(record: logging.LogRecord) -> str:
    value = datetime.fromtimestamp(
        record.created,
        tz=timezone.utc,
    )
    return value.isoformat(timespec="milliseconds")


def _context_value(
    record: logging.LogRecord,
    field: str,
    fallback: str,
) -> str:
    value = getattr(record, field, "")
    return str(value or fallback or "")


def _safe_exception_text(
    formatter: logging.Formatter,
    record: logging.LogRecord,
) -> str:
    if not record.exc_info:
        return ""

    return sanitize_text(
        formatter.formatException(record.exc_info)
    )


def _extra_fields(record: logging.LogRecord) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in record.__dict__.items():
        if key in _STANDARD_RECORD_FIELDS:
            continue

        if key in {
            "request_id",
            "request_method",
            "request_path",
            "message",
            "asctime",
        }:
            continue

        result[str(key)] = sanitize_text(value)

    return result


class RequestContextFilter(logging.Filter):
    """
    向所有日志记录注入当前 HTTP 请求上下文。
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "request_id", ""):
            record.request_id = get_request_id()

        if not getattr(record, "request_method", ""):
            record.request_method = get_request_method()

        if not getattr(record, "request_path", ""):
            record.request_path = get_request_path()

        return True


class SafeTextFormatter(logging.Formatter):
    """
    适用于本地开发的人类可读日志格式。
    """

    def format(self, record: logging.LogRecord) -> str:
        request_id = _context_value(
            record,
            "request_id",
            get_request_id(),
        )
        method = _context_value(
            record,
            "request_method",
            get_request_method(),
        )
        path = _context_value(
            record,
            "request_path",
            get_request_path(),
        )

        message = sanitize_text(record.getMessage())

        context_parts: list[str] = []

        if request_id:
            context_parts.append(f"request_id={request_id}")
        if method:
            context_parts.append(f"method={method}")
        if path:
            context_parts.append(f"path={path}")

        context = " ".join(context_parts)

        line = (
            f"{_utc_timestamp(record)} "
            f"[{record.levelname}] "
            f"{record.name}"
        )

        if context:
            line = f"{line} [{context}]"

        line = f"{line}: {message}"

        exception_text = _safe_exception_text(self, record)
        if exception_text:
            line = f"{line}\n{exception_text}"

        return line


class SafeJsonFormatter(logging.Formatter):
    """
    适用于生产日志采集系统的 JSON Lines 格式。
    """

    def format(self, record: logging.LogRecord) -> str:
        request_id = _context_value(
            record,
            "request_id",
            get_request_id(),
        )
        method = _context_value(
            record,
            "request_method",
            get_request_method(),
        )
        path = _context_value(
            record,
            "request_path",
            get_request_path(),
        )

        payload: dict[str, Any] = {
            "timestamp": _utc_timestamp(record),
            "level": record.levelname,
            "logger": record.name,
            "message": sanitize_text(record.getMessage()),
            "request_id": request_id,
            "method": method,
            "path": path,
        }

        exception_text = _safe_exception_text(self, record)
        if exception_text:
            payload["exception"] = exception_text

        extra = _extra_fields(record)
        if extra:
            payload["extra"] = extra

        return json.dumps(
            payload,
            ensure_ascii=False,
            default=str,
            separators=(",", ":"),
        )


def setup_logger(
    level: str = "INFO",
    *,
    log_format: str | None = None,
) -> None:
    """
    初始化项目日志。

    LOG_FORMAT=text:
        本地可读格式。

    LOG_FORMAT=json:
        生产 JSON Lines 格式。
    """

    normalized_level = getattr(
        logging,
        level.upper(),
        logging.INFO,
    )

    normalized_format = (
        log_format
        or os.getenv("LOG_FORMAT", "text")
    ).strip().lower()

    formatter: logging.Formatter

    if normalized_format == "json":
        formatter = SafeJsonFormatter()
    else:
        formatter = SafeTextFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(normalized_level)
    handler.addFilter(RequestContextFilter())
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(normalized_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    logging.captureWarnings(True)