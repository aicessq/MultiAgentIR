"""
异常处理模块
定义应用级别的自定义异常和错误处理
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class BaseAppError(Exception):
    """
    应用基础异常类
    所有自定义异常的基类
    """
    
    def __init__(
        self,
        message: str = "应用内部错误",
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将异常转换为字典格式，用于 API 响应
        """
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class ValidationError(BaseAppError):
    """
    数据验证错误
    """
    
    def __init__(
        self,
        message: str = "数据验证失败",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class AuthenticationError(BaseAppError):
    """
    认证错误
    """
    
    def __init__(
        self,
        message: str = "认证失败",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class AuthorizationError(BaseAppError):
    """
    授权错误
    """
    
    def __init__(
        self,
        message: str = "权限不足",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class NotFoundError(BaseAppError):
    """
    资源未找到错误
    """
    
    def __init__(
        self,
        message: str = "资源未找到",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="NOT_FOUND_ERROR",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ModelError(BaseAppError):
    """
    模型调用错误
    """
    
    def __init__(
        self,
        message: str = "模型调用失败",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="MODEL_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class RateLimitError(BaseAppError):
    """
    速率限制错误
    """
    
    def __init__(
        self,
        message: str = "请求频率超限",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="RATE_LIMIT_ERROR",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )


class ConfigurationError(BaseAppError):
    """
    配置错误
    """
    
    def __init__(
        self,
        message: str = "配置错误",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class ExternalServiceError(BaseAppError):
    """
    外部服务错误
    """
    
    def __init__(
        self,
        message: str = "外部服务异常",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="EXTERNAL_SERVICE_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


class TaskError(BaseAppError):
    """
    任务执行错误
    """
    
    def __init__(
        self,
        message: str = "任务执行失败",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="TASK_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class AgentError(BaseAppError):
    """
    Agent 执行错误
    """
    
    def __init__(
        self,
        message: str = "Agent 执行失败",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="AGENT_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class TopologyError(BaseAppError):
    """
    拓扑执行错误
    """

    def __init__(
        self,
        message: str = "拓扑执行失败",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="TOPOLOGY_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class TaskNotFoundError(BaseAppError):
    """
    任务未找到错误
    """

    def __init__(
        self,
        task_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=f"任务未找到: {task_id}",
            code="TASK_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details or {"task_id": task_id},
        )


def handle_app_error(exc: BaseAppError) -> HTTPException:
    """
    将应用异常转换为 FastAPI HTTPException
    """
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.to_dict(),
    )