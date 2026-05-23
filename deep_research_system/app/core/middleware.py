"""
中间件模块
实现全局异常处理、请求日志等中间件
"""

import time
import uuid
from typing import Callable, Dict, Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import BaseAppError, handle_app_error
from app.core.logging import log_request, log_response, get_logger
from app.schemas.response import error_response

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    请求ID中间件
    为每个请求生成唯一的请求ID
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求，生成请求ID
        """
        # 生成或获取请求ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # 将请求ID添加到请求状态
        request.state.request_id = request_id
        
        # 继续处理请求
        response = await call_next(request)
        
        # 在响应头中添加请求ID
        response.headers["X-Request-ID"] = request_id
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件
    记录所有请求和响应的详细信息
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        记录请求和响应日志
        """
        # 记录请求开始时间
        start_time = time.time()
        
        # 获取请求信息
        request_id = getattr(request.state, "request_id", "unknown")
        method = request.method
        url = str(request.url)
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent")
        
        # 记录请求日志
        log_request(
            request_id=request_id,
            method=method,
            url=url,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算请求耗时
            duration_ms = (time.time() - start_time) * 1000
            
            # 记录响应日志
            log_response(
                request_id=request_id,
                method=method,
                url=url,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            
            return response
            
        except Exception as exc:
            # 计算请求耗时
            duration_ms = (time.time() - start_time) * 1000
            
            # 记录异常日志
            log_response(
                request_id=request_id,
                method=method,
                url=url,
                status_code=500,
                duration_ms=duration_ms,
                error=str(exc),
            )
            
            # 重新抛出异常，让异常处理中间件处理
            raise


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """
    异常处理中间件
    捕获并统一处理所有异常
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        捕获并处理异常
        """
        try:
            return await call_next(request)
            
        except BaseAppError as exc:
            logger.bind(
                request_id=getattr(request.state, "request_id", "unknown"),
                exception_code=exc.code,
            ).error(f"应用异常: {exc.code} - {exc.message}")

            return JSONResponse(
                status_code=exc.status_code,
                content=error_response(
                    code=exc.code,
                    message=exc.message,
                    details=exc.details,
                ),
            )

        except Exception as exc:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.bind(request_id=request_id).opt(exception=True).error(
                f"未捕获异常: {type(exc).__name__}"
            )

            if settings.ENVIRONMENT == "production":
                message = "服务器内部错误"
                details = None
            else:
                message = f"{type(exc).__name__}: {str(exc)}"
                details = None

            return JSONResponse(
                status_code=500,
                content=error_response(
                    code="INTERNAL_SERVER_ERROR",
                    message=message,
                    details=details,
                ),
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    安全头中间件
    添加安全相关的 HTTP 头
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        添加安全头
        """
        response = await call_next(request)
        
        # 添加安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # 根据环境添加 CSP
        if settings.ENVIRONMENT == "production":
            response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response


def setup_middlewares(app: FastAPI) -> None:
    """
    设置所有中间件
    """
    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 请求ID中间件
    app.add_middleware(RequestIDMiddleware)
    
    # 请求日志中间件
    app.add_middleware(RequestLoggingMiddleware)
    
    # 异常处理中间件
    app.add_middleware(ExceptionHandlingMiddleware)
    
    # 安全头中间件
    app.add_middleware(SecurityHeadersMiddleware)
    
    logger.info("中间件设置完成")