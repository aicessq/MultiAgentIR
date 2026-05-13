"""
日志配置模块
配置结构化 JSON 日志
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger
from app.core.config import settings


class InterceptHandler(logging.Handler):
    """
    拦截标准 logging 模块的日志，转发到 loguru
    """
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        发射日志记录
        """
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        
        # 获取 loguru 的 frame
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        
        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


def serialize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    序列化日志记录
    """
    subset = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["name"],
    }
    
    # 添加上下文信息
    if "extra" in record and record["extra"]:
        subset.update(record["extra"])
    
    # 添加异常信息
    if "exception" in record and record["exception"]:
        subset["exception"] = str(record["exception"])
    
    # 添加函数名和行号
    if "function" in record:
        subset["function"] = record["function"]
    if "line" in record:
        subset["line"] = record["line"]
    
    return subset


def formatter(record: Dict[str, Any]) -> str:
    """
    日志格式化器
    返回 JSON 格式的日志
    """
    record["extra"]["serialized"] = serialize_record(record)
    return json.dumps(record["extra"]["serialized"], ensure_ascii=False)


def setup_logging() -> None:
    """
    设置日志配置
    """
    # 移除默认的 loguru 处理器
    logger.remove()
    
    # 添加控制台输出（JSON 格式）
    logger.add(
        sys.stdout,
        format=formatter,
        level=settings.LOG_LEVEL.upper(),
        serialize=False,  # 我们自己在 formatter 中序列化
        colorize=False,   # JSON 格式不需要颜色
        backtrace=True,
        diagnose=True,
    )
    
    # 添加文件输出（可选）
    if settings.ENVIRONMENT == "production":
        logger.add(
            "logs/app_{time:YYYY-MM-DD}.log",
            rotation="00:00",  # 每天轮转
            retention="30 days",  # 保留30天
            compression="zip",
            format=formatter,
            level="INFO",
            serialize=False,
        )
    
    # 拦截标准 logging 模块
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # 设置第三方库的日志级别
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False
    
    # 设置根日志记录器
    root_logger = logging.getLogger()
    root_logger.handlers = [InterceptHandler()]
    
    logger.info("日志系统初始化完成", extra={"environment": settings.ENVIRONMENT})


def get_logger(name: Optional[str] = None) -> logger:
    """
    获取日志记录器
    """
    if name:
        return logger.bind(module=name)
    return logger


# 日志上下文管理器
class LogContext:
    """
    日志上下文管理器
    用于在日志中添加额外上下文信息
    """
    
    def __init__(self, **context):
        self.context = context
        self.logger = logger
    
    def __enter__(self):
        self.logger = logger.bind(**self.context)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


# 常用日志辅助函数
def log_request(
    request_id: str,
    method: str,
    url: str,
    client_ip: str,
    user_agent: Optional[str] = None,
    **extra
) -> None:
    """
    记录请求日志
    """
    context = {
        "request_id": request_id,
        "method": method,
        "url": url,
        "client_ip": client_ip,
        "type": "request",
    }
    
    if user_agent:
        context["user_agent"] = user_agent
    
    context.update(extra)
    
    with LogContext(**context):
        logger.info(f"{method} {url}")


def log_response(
    request_id: str,
    method: str,
    url: str,
    status_code: int,
    duration_ms: float,
    **extra
) -> None:
    """
    记录响应日志
    """
    context = {
        "request_id": request_id,
        "method": method,
        "url": url,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "type": "response",
    }
    
    context.update(extra)
    
    level = "INFO" if status_code < 400 else "WARNING"
    
    with LogContext(**context):
        logger.log(level, f"{method} {url} {status_code} ({duration_ms:.2f}ms)")


def log_model_call(
    model: str,
    provider: str,
    duration_ms: float,
    token_usage: Optional[Dict[str, int]] = None,
    cost: Optional[float] = None,
    **extra
) -> None:
    """
    记录模型调用日志
    """
    context = {
        "model": model,
        "provider": provider,
        "duration_ms": duration_ms,
        "type": "model_call",
    }
    
    if token_usage:
        context["token_usage"] = token_usage
    
    if cost is not None:
        context["cost"] = cost
    
    context.update(extra)
    
    with LogContext(**context):
        logger.info(f"Model call: {model} ({provider}) - {duration_ms:.2f}ms")


def log_agent_execution(
    agent: str,
    duration_ms: float,
    status: str = "success",
    error: Optional[str] = None,
    **extra
) -> None:
    """
    记录 Agent 执行日志
    """
    context = {
        "agent": agent,
        "duration_ms": duration_ms,
        "status": status,
        "type": "agent_execution",
    }
    
    if error:
        context["error"] = error
    
    context.update(extra)
    
    level = "INFO" if status == "success" else "ERROR"
    
    with LogContext(**context):
        logger.log(level, f"Agent execution: {agent} - {status} ({duration_ms:.2f}ms)")


def log_topology_execution(
    topology: str,
    task_id: str,
    duration_ms: float,
    status: str = "success",
    **extra
) -> None:
    """
    记录拓扑执行日志
    """
    context = {
        "topology": topology,
        "task_id": task_id,
        "duration_ms": duration_ms,
        "status": status,
        "type": "topology_execution",
    }
    
    context.update(extra)
    
    level = "INFO" if status == "success" else "ERROR"
    
    with LogContext(**context):
        logger.log(level, f"Topology execution: {topology} - {status} ({duration_ms:.2f}ms)")