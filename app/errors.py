"""
文件名: errors.py
描述: API 层错误辅助与结构化错误响应。
主要功能:
    - 构建统一 schema 的错误响应体。
    - 提供 AppError 用于一致的异常处理。
依赖: fastapi
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from fastapi import Request
from fastapi.responses import JSONResponse

# ============================================
# region 错误模型
# ============================================


@dataclass(frozen=True)
class ErrorDetail:
    """
    字段级错误详情，用于校验失败响应。
    """

    field: str
    code: str
    message: str


class AppError(Exception):
    """
    领域异常，用于统一 API 错误映射。
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Iterable[ErrorDetail]] = None,
    ) -> None:
        """
        创建应用错误实例。

        参数:
            status_code: 返回的 HTTP 状态码。
            code: 错误码字符串。
            message: 可读错误信息。
            details: 字段级错误列表（可选）。
        """
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = list(details or [])


# endregion
# ============================================

# ============================================
# region 错误响应
# ============================================


def _request_id_from(request: Request) -> str:
    """
    获取 request.state 中的 request_id。

    参数:
        request: FastAPI 请求对象。
    返回:
        请求标识字符串。
    """
    return getattr(request.state, "request_id", "unknown")


def build_error_payload(
    *,
    code: str,
    message: str,
    request_id: str,
    details: Optional[Iterable[ErrorDetail]] = None,
) -> dict:
    """
    构建标准错误响应 payload。

    参数:
        code: 错误码字符串。
        message: 可读错误信息。
        request_id: 请求标识字符串。
        details: 字段级错误列表（可选）。
    返回:
        错误响应字典。
    """
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "details": [
                {"field": d.field, "code": d.code, "message": d.message}
                for d in (details or [])
            ],
        }
    }


def error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: Optional[Iterable[ErrorDetail]] = None,
) -> JSONResponse:
    """
    生成标准错误 schema 的 JSONResponse。

    参数:
        request: FastAPI 请求对象。
        status_code: 返回的 HTTP 状态码。
        code: 错误码字符串。
        message: 可读错误信息。
        details: 字段级错误列表（可选）。
    返回:
        包含错误 schema 与 request_id 头的 JSONResponse。
    """
    payload = build_error_payload(
        code=code,
        message=message,
        request_id=_request_id_from(request),
        details=details,
    )
    return JSONResponse(
        status_code=status_code,
        content=payload,
        headers={"X-Request-ID": _request_id_from(request)},
    )


# endregion
# ============================================

# ============================================
# region 资源校验
# ============================================


def ensure_exists(resource: object, *, code: str, field: str, message: str) -> None:
    """
    校验资源是否存在。

    参数:
        resource: 资源对象或 None。
        code: 资源缺失时的错误码。
        field: 错误详情字段名。
        message: 可读错误信息。
    """
    if resource is None:
        raise AppError(
            status_code=404,
            code=code,
            message=message,
            details=[ErrorDetail(field=field, code="NOT_FOUND", message=message)],
        )


def ensure_available(
    status: str,
    *,
    unavailable: Iterable[str],
    code: str,
    field: str,
    message: str,
) -> None:
    """
    基于状态校验资源可用性。

    参数:
        status: 当前资源状态。
        unavailable: 不可用状态集合。
        code: 不可用时的错误码。
        field: 错误详情字段名。
        message: 可读错误信息。
    """
    if status in set(unavailable):
        raise AppError(
            status_code=403,
            code=code,
            message=message,
            details=[ErrorDetail(field=field, code="UNAVAILABLE", message=message)],
        )


# endregion
# ============================================
