"""
API 路由整合模块
整合所有 API 路由到统一的路由器
"""

from fastapi import APIRouter

from app.api.routes_health import router as health_router
from app.api.routes_research import router as research_router
from app.api.routes_models import router as models_router

# 创建主 API 路由器
api_router = APIRouter()

# 包含健康检查路由
api_router.include_router(health_router)

# 包含研究和模型路由
api_router.include_router(research_router, tags=["research"])
api_router.include_router(models_router, tags=["models"])

# 根端点，提供 API 基本信息
@api_router.get("/")
async def root():
    """
    API 根端点
    返回 API 基本信息
    """
    return {
        "message": "Deep Research System API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": [
            {"path": "/health", "methods": ["GET"], "description": "健康检查"},
            {"path": "/health/ready", "methods": ["GET"], "description": "就绪检查"},
            {"path": "/health/live", "methods": ["GET"], "description": "存活检查"},
            {"path": "/health/info", "methods": ["GET"], "description": "系统信息"},
            # 后续添加的其他端点
        ]
    }