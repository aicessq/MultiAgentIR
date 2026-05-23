"""
健康检查路由模块
提供系统健康状态检查端点
"""

import time
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.schemas.response import HealthResponse, success_response

# 创建健康检查路由
router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """
    健康检查端点
    返回系统健康状态和依赖服务状态
    """
    timestamp = datetime.utcnow().isoformat() + "Z"
    return success_response(data={
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": timestamp,
        "dependencies": {
            "models": "available",
            "config": "loaded",
        },
    })


@router.get("/ready")
async def readiness_check() -> JSONResponse:
    """
    就绪检查端点
    检查服务是否准备好接收流量
    """
    # 这里可以添加更详细的服务就绪检查
    # 例如：数据库连接、Redis连接、模型API可用性等
    
    return success_response(
        data={
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "services": {
                "api": "ready",
                "config": "loaded",
                "dependencies": "checking",
            }
        },
        msg="服务就绪"
    )


@router.get("/live")
async def liveness_check() -> JSONResponse:
    """
    存活检查端点
    检查服务是否存活（Kubernetes liveness probe）
    """
    # 简单的存活检查，只返回成功状态
    return success_response(
        data={
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
        msg="服务存活"
    )


@router.get("/info")
async def system_info() -> JSONResponse:
    """
    系统信息端点
    返回系统配置信息和版本信息
    """
    # 构建系统信息
    system_info_data = {
        "project": {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
        },
        "server": {
            "host": settings.HOST,
            "port": settings.PORT,
            "reload": settings.RELOAD,
        },
        "api": {
            "version": settings.API_V1_STR,
            "docs_enabled": settings.DOCS_ENABLED,
        },
        "models": {
            "deepseek": {
                "enabled": bool(settings.DEEPSEEK_API_KEY),
                "model": settings.DEEPSEEK_MODEL,
            },
            "zhipu": {
                "enabled": bool(settings.ZHIPU_API_KEY),
                "model": settings.ZHIPU_MODEL,
            },
            "kimi": {
                "enabled": bool(settings.KIMI_API_KEY),
                "model": settings.KIMI_MODEL,
            },
            "doubao": {
                "enabled": bool(settings.DOUBAO_API_KEY),
                "model": settings.DOUBAO_MODEL,
            },
            "ernie": {
                "enabled": bool(settings.ERNIE_API_KEY),
                "model": settings.ERNIE_MODEL,
            },
            "qwen": {
                "enabled": bool(settings.QWEN_API_KEY),
                "model": settings.QWEN_MODEL,
            },
        },
        "performance": {
            "max_concurrent_requests": settings.MAX_CONCURRENT_REQUESTS,
            "max_concurrent_searches": settings.MAX_CONCURRENT_SEARCHES,
            "request_timeout": settings.REQUEST_TIMEOUT,
            "model_timeout": settings.MODEL_TIMEOUT,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    
    return success_response(data=system_info_data, msg="系统信息")