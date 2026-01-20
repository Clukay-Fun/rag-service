"""
文件名: main.py
描述: FastAPI 应用工厂与全局中间件。
主要功能:
    - 创建 FastAPI 应用并挂载 request_id 日志与错误处理。
    - 提供模块级 app 供 ASGI 服务器加载。
依赖: fastapi, pydantic
"""

from __future__ import annotations

import json
import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError

from .api.cleanup_tasks import router as cleanup_task_router
from .api.documents import router as document_router
from .api.knowledge_bases import router as knowledge_base_router
from .config import get_settings
from .errors import AppError, ErrorDetail, error_response

# ============================================
# region 辅助函数
# ============================================


def _http_error_code(status_code: int) -> str:
    """
    将 HTTP 状态码映射为标准错误码。

    参数:
        status_code: HTTP 状态码整数。
    返回:
        错误码字符串。
    """
    mapping = {
        400: "VALIDATION_ERROR",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        413: "PAYLOAD_TOO_LARGE",
        415: "UNSUPPORTED_MEDIA_TYPE",
        503: "SERVICE_UNAVAILABLE",
    }
    return mapping.get(status_code, "HTTP_ERROR")


def _setup_logging(level: str) -> logging.Logger:
    """
    配置服务日志。

    参数:
        level: 日志级别名称。
    返回:
        配置后的 logger 实例。
    """
    logging.basicConfig(level=level)
    return logging.getLogger("rag_service")


# endregion
# ============================================

# ============================================
# region 应用工厂
# ============================================


def create_app() -> FastAPI:
    """
    创建并配置 FastAPI 应用。

    返回:
        FastAPI 应用实例。
    """
    settings = get_settings()
    logger = _setup_logging(settings.log_level)

    app = FastAPI()
    app.state.settings = settings
    app.state.logger = logger

    # ============================================
    # region 路由注册
    # ============================================

    app.include_router(knowledge_base_router)
    app.include_router(cleanup_task_router)
    app.include_router(document_router)

    # endregion
    # ============================================

    # ============================================
    # region 中间件
    # ============================================

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        """
        分配 request_id、记录请求日志并设置响应头。
        """
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            status_code = 500
            if isinstance(exc, AppError):
                status_code = exc.status_code
            elif isinstance(exc, HTTPException):
                status_code = exc.status_code
            elif isinstance(exc, RequestValidationError):
                status_code = 400
            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.error(
                json.dumps(
                    {
                        "event": "request",
                        "method": request.method,
                        "path": request.url.path,
                        "status": status_code,
                        "duration_ms": duration_ms,
                        "request_id": request_id,
                    }
                )
            )
            raise
        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            json.dumps(
                {
                    "event": "request",
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "request_id": request_id,
                }
            )
        )
        return response

    # endregion
    # ============================================

    # ============================================
    # region 异常处理
    # ============================================

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        """
        将 AppError 转换为标准错误响应。
        """
        return error_response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """
        将校验错误转换为标准错误响应。
        """
        details = []
        for err in exc.errors():
            loc = ".".join(str(part) for part in err.get("loc", []) if part != "body")
            details.append(
                ErrorDetail(
                    field=loc or "body",
                    code="INVALID",
                    message=str(err.get("msg", "Invalid request")),
                )
            )
        return error_response(
            request,
            status_code=400,
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details=details,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """
        将 HTTPException 转换为标准错误响应。
        """
        return error_response(
            request,
            status_code=exc.status_code,
            code=_http_error_code(exc.status_code),
            message=str(exc.detail),
            details=None,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """
        将未处理异常转换为标准 500 响应。
        """
        logger.exception(
            "Unhandled error",
            extra={"request_id": getattr(request.state, "request_id", "unknown")},
        )
        return error_response(
            request,
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            details=None,
        )

    # endregion
    # ============================================

    return app


# endregion
# ============================================

# ============================================
# region ASGI 应用
# ============================================

app = create_app()

# endregion
# ============================================
