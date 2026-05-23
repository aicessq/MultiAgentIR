#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deep Research System 主入口文件

基于 FastAPI + LangGraph 的多 Agent 智能检索分析系统
用于深度研究、信息检索和智能分析
"""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.api.routes import api_router


# 设置日志
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    负责启动和关闭时的资源管理：
    1. 启动时：初始化数据库连接、加载模型、预热缓存
    2. 关闭时：清理资源、关闭连接
    """
    logger.info("🚀 Deep Research System 正在启动...")
    
    # TODO: 初始化数据库连接
    # TODO: 加载预训练模型
    # TODO: 预热缓存
    
    logger.info("✅ Deep Research System 启动完成")
    
    yield
    
    logger.info("🛑 Deep Research System 正在关闭...")
    
    # TODO: 清理资源
    # TODO: 关闭数据库连接
    
    logger.info("👋 Deep Research System 已关闭")


def create_application() -> FastAPI:
    """
    创建 FastAPI 应用实例
    
    配置应用的基本设置、中间件、路由等
    """
    # 创建 FastAPI 应用
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="基于 FastAPI + LangGraph 的多 Agent 智能检索分析系统",
        version=settings.VERSION,
        docs_url="/docs" if settings.DOCS_ENABLED else None,
        redoc_url="/redoc" if settings.DOCS_ENABLED else None,
        lifespan=lifespan,
    )
    
    # 设置中间件
    from app.core.middleware import setup_middlewares
    setup_middlewares(app)
    
    # 添加 API 路由
    app.include_router(api_router, prefix="/api")
    
    return app


# 创建应用实例
app = create_application()


if __name__ == "__main__":
    """
    直接运行时的入口点
    
    用于开发环境调试，生产环境应使用 uvicorn 命令启动
    """
    import uvicorn
    
    logger.info(f"🌐 启动服务在 {settings.HOST}:{settings.PORT}")
    logger.info(f"📚 API 文档: http://{settings.HOST}:{settings.PORT}/docs")
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
    )