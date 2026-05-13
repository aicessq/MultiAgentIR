"""
API 响应模型模块
定义统一的 API 响应格式
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

from app.core.errors import BaseAppError

T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    """
    统一 API 响应模型
    所有 API 端点都应返回此格式的响应
    """
    
    code: int = Field(default=0, description="响应状态码，0 表示成功")
    msg: str = Field(default="success", description="响应消息")
    data: Optional[T] = Field(default=None, description="响应数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 0,
                "msg": "success",
                "data": {"result": "操作成功"}
            }
        }


class ErrorResponse(BaseModel):
    """
    错误响应模型
    """
    
    code: str = Field(description="错误代码")
    message: str = Field(description="错误消息")
    details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情")
    
    @classmethod
    def from_exception(cls, exc: BaseAppError) -> "ErrorResponse":
        """
        从异常对象创建错误响应
        """
        return cls(
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "VALIDATION_ERROR",
                "message": "数据验证失败",
                "details": {"field": "username", "error": "不能为空"}
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """
    分页响应模型
    """
    
    items: List[T] = Field(description="数据列表")
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    size: int = Field(description="每页大小")
    pages: int = Field(description="总页数")
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [{"id": 1, "name": "项目1"}],
                "total": 100,
                "page": 1,
                "size": 10,
                "pages": 10
            }
        }


class HealthResponse(BaseModel):
    """
    健康检查响应模型
    """
    
    status: str = Field(description="服务状态")
    version: str = Field(description="应用版本")
    environment: str = Field(description="运行环境")
    timestamp: str = Field(description="检查时间戳")
    dependencies: Dict[str, str] = Field(description="依赖服务状态")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "environment": "development",
                "timestamp": "2024-01-01T00:00:00Z",
                "dependencies": {
                    "redis": "connected",
                    "database": "connected",
                    "models": "available"
                }
            }
        }


class TaskStatusResponse(BaseModel):
    """
    任务状态响应模型
    """
    
    task_id: str = Field(description="任务ID")
    status: str = Field(description="任务状态")
    progress: int = Field(description="进度百分比")
    current_stage: Optional[str] = Field(default=None, description="当前阶段")
    result: Optional[Dict[str, Any]] = Field(default=None, description="任务结果")
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_abc123",
                "status": "running",
                "progress": 45,
                "current_stage": "analyzer",
                "result": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:01Z"
            }
        }


class ModelStatusResponse(BaseModel):
    """
    模型状态响应模型
    """
    
    name: str = Field(description="模型名称")
    provider: str = Field(description="模型提供商")
    enabled: bool = Field(description="是否启用")
    status: str = Field(description="模型状态")
    available_keys: int = Field(description="可用API Key数量")
    total_calls: int = Field(description="总调用次数")
    success_rate: float = Field(description="成功率")
    avg_latency_ms: float = Field(description="平均延迟(毫秒)")
    last_error: Optional[str] = Field(default=None, description="最后错误信息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "deepseek-chat",
                "provider": "deepseek",
                "enabled": True,
                "status": "healthy",
                "available_keys": 2,
                "total_calls": 150,
                "success_rate": 0.98,
                "avg_latency_ms": 1250.5,
                "last_error": None
            }
        }


class CostMetricsResponse(BaseModel):
    """
    成本指标响应模型
    """
    
    total_cost: float = Field(description="总成本")
    total_tokens: int = Field(description="总Token数")
    cost_by_model: Dict[str, float] = Field(description="按模型统计的成本")
    cost_by_agent: Dict[str, float] = Field(description="按Agent统计的成本")
    cost_by_topology: Dict[str, float] = Field(description="按拓扑统计的成本")
    timestamp: str = Field(description="统计时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_cost": 0.42,
                "total_tokens": 12500,
                "cost_by_model": {
                    "deepseek-chat": 0.15,
                    "glm-4": 0.20,
                    "qwen-max": 0.07
                },
                "cost_by_agent": {
                    "planner": 0.05,
                    "searcher": 0.10,
                    "analyzer": 0.15,
                    "writer": 0.12
                },
                "cost_by_topology": {
                    "hierarchical": 0.30,
                    "debate": 0.12
                },
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }


def success_response(data: Optional[T] = None, msg: str = "success") -> ResponseModel[T]:
    """
    创建成功响应
    """
    return ResponseModel(code=0, msg=msg, data=data)


def error_response(
    code: str = "INTERNAL_ERROR",
    message: str = "内部错误",
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    创建错误响应
    """
    return {
        "code": code,
        "message": message,
        "details": details or {},
    }