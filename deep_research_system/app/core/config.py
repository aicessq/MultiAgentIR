"""
应用配置模块
基于 pydantic-settings 的环境变量配置管理
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    应用配置类
    从环境变量和 .env 文件加载配置
    """
    
    # 应用基础配置
    PROJECT_NAME: str = "Deep Research System"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"  # development, testing, production
    DEBUG: bool = True
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    LOG_LEVEL: str = "info"
    
    # API 配置
    API_V1_STR: str = "/api/v1"
    DOCS_ENABLED: bool = True
    
    # CORS 配置
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """
        处理 CORS 来源配置
        支持字符串和列表两种格式
        """
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_SSL: bool = False
    REDIS_POOL_MIN_SIZE: int = 1
    REDIS_POOL_MAX_SIZE: int = 10
    
    # 国产模型 API 配置
    # DeepSeek
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_MAX_TOKENS: int = 8192
    DEEPSEEK_TEMPERATURE: float = 0.7
    
    # 智谱AI
    ZHIPU_API_KEY: Optional[str] = None
    ZHIPU_API_BASE: str = "https://open.bigmodel.cn/api/paas/v4"
    ZHIPU_MODEL: str = "glm-4"
    ZHIPU_MAX_TOKENS: int = 8192
    ZHIPU_TEMPERATURE: float = 0.7
    
    # 月之暗面
    KIMI_API_KEY: Optional[str] = None
    KIMI_API_BASE: str = "https://api.moonshot.cn/v1"
    KIMI_MODEL: str = "moonshot-v1-8k"
    KIMI_MAX_TOKENS: int = 8192
    KIMI_TEMPERATURE: float = 0.7
    
    # 豆包
    DOUBAO_API_KEY: Optional[str] = None
    DOUBAO_API_BASE: str = "https://ark.cn-beijing.volces.com/api/v3"
    DOUBAO_MODEL: str = "ep-20240610112120-abcdefg"
    DOUBAO_MAX_TOKENS: int = 4096
    DOUBAO_TEMPERATURE: float = 0.7
    
    # 百度文心一言
    ERNIE_API_KEY: Optional[str] = None
    ERNIE_API_BASE: str = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop"
    ERNIE_MODEL: str = "ernie-4.0-8k"
    ERNIE_MAX_TOKENS: int = 8192
    ERNIE_TEMPERATURE: float = 0.7
    
    # 阿里通义千问
    QWEN_API_KEY: Optional[str] = None
    QWEN_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen-max"
    QWEN_MAX_TOKENS: int = 8192
    QWEN_TEMPERATURE: float = 0.7
    
    # 搜索服务配置
    SERPER_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    GOOGLE_CSE_ID: Optional[str] = None
    GOOGLE_API_KEY_FOR_SEARCH: Optional[str] = None
    
    # 性能配置
    MAX_CONCURRENT_REQUESTS: int = 10
    MAX_CONCURRENT_SEARCHES: int = 5
    BATCH_SIZE: int = 10
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 1  # 秒
    REQUEST_TIMEOUT: int = 30
    MODEL_TIMEOUT: int = 60
    
    # 缓存配置
    CACHE_TTL: int = 3600  # 1小时
    SEARCH_CACHE_TTL: int = 1800  # 30分钟
    MODEL_CACHE_TTL: int = 86400  # 24小时
    
    # 安全配置
    SECRET_KEY: str = "your-super-secret-jwt-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # 文件存储
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 104857600  # 100MB
    
    # 模型配置
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # 忽略未定义的额外环境变量
    )
    
    def get_model_api_key(self, provider: str) -> Optional[str]:
        """
        根据模型提供商获取 API Key
        """
        provider_key_map = {
            "deepseek": self.DEEPSEEK_API_KEY,
            "zhipu": self.ZHIPU_API_KEY,
            "kimi": self.KIMI_API_KEY,
            "doubao": self.DOUBAO_API_KEY,
            "ernie": self.ERNIE_API_KEY,
            "qwen": self.QWEN_API_KEY,
        }
        return provider_key_map.get(provider.lower())
    
    def get_model_api_base(self, provider: str) -> Optional[str]:
        """
        根据模型提供商获取 API Base URL
        """
        provider_base_map = {
            "deepseek": self.DEEPSEEK_API_BASE,
            "zhipu": self.ZHIPU_API_BASE,
            "kimi": self.KIMI_API_BASE,
            "doubao": self.DOUBAO_API_BASE,
            "ernie": self.ERNIE_API_BASE,
            "qwen": self.QWEN_API_BASE,
        }
        return provider_base_map.get(provider.lower())
    
    def get_model_config(self, provider: str) -> Dict[str, Any]:
        """
        获取指定模型提供商的完整配置
        """
        config_map = {
            "deepseek": {
                "api_key": self.DEEPSEEK_API_KEY,
                "api_base": self.DEEPSEEK_API_BASE,
                "model": self.DEEPSEEK_MODEL,
                "max_tokens": self.DEEPSEEK_MAX_TOKENS,
                "temperature": self.DEEPSEEK_TEMPERATURE,
            },
            "zhipu": {
                "api_key": self.ZHIPU_API_KEY,
                "api_base": self.ZHIPU_API_BASE,
                "model": self.ZHIPU_MODEL,
                "max_tokens": self.ZHIPU_MAX_TOKENS,
                "temperature": self.ZHIPU_TEMPERATURE,
            },
            "kimi": {
                "api_key": self.KIMI_API_KEY,
                "api_base": self.KIMI_API_BASE,
                "model": self.KIMI_MODEL,
                "max_tokens": self.KIMI_MAX_TOKENS,
                "temperature": self.KIMI_TEMPERATURE,
            },
            "doubao": {
                "api_key": self.DOUBAO_API_KEY,
                "api_base": self.DOUBAO_API_BASE,
                "model": self.DOUBAO_MODEL,
                "max_tokens": self.DOUBAO_MAX_TOKENS,
                "temperature": self.DOUBAO_TEMPERATURE,
            },
            "ernie": {
                "api_key": self.ERNIE_API_KEY,
                "api_base": self.ERNIE_API_BASE,
                "model": self.ERNIE_MODEL,
                "max_tokens": self.ERNIE_MAX_TOKENS,
                "temperature": self.ERNIE_TEMPERATURE,
            },
            "qwen": {
                "api_key": self.QWEN_API_KEY,
                "api_base": self.QWEN_API_BASE,
                "model": self.QWEN_MODEL,
                "max_tokens": self.QWEN_MAX_TOKENS,
                "temperature": self.QWEN_TEMPERATURE,
            },
        }
        return config_map.get(provider.lower(), {})


# 全局配置实例
settings = Settings()