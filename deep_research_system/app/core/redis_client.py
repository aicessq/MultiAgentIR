"""
Redis 客户端模块
实现 Redis 单例客户端、连接池管理和基础操作封装
"""

import asyncio
import json
import pickle
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import timedelta

import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import (
    ConnectionError,
    TimeoutError,
    RedisError,
    AuthenticationError,
    ResponseError,
)

from app.core.config import settings
from app.core.errors import ExternalServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisClient:
    """
    Redis 客户端封装类
    提供单例模式和连接池管理
    """
    
    _instance: Optional["RedisClient"] = None
    _redis_client: Optional[Redis] = None
    _connection_pool: Optional[ConnectionPool] = None
    
    def __new__(cls):
        """
        单例模式实现
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """
        初始化 Redis 客户端
        """
        if self._initialized:
            return
        
        self._initialized = True
        self._connect()
        
        logger.info("Redis 客户端初始化完成")
    
    def _connect(self) -> None:
        """
        连接 Redis 服务器
        """
        try:
            # 构建连接参数
            connection_kwargs = {
                "host": settings.REDIS_HOST,
                "port": settings.REDIS_PORT,
                "db": settings.REDIS_DB,
                "encoding": "utf-8",
                "decode_responses": True,
                "socket_connect_timeout": 5,
                "socket_timeout": 5,
                "retry_on_timeout": True,
                "max_connections": settings.REDIS_POOL_MAX_SIZE,
            }
            
            # 添加密码（如果有）
            if settings.REDIS_PASSWORD:
                connection_kwargs["password"] = settings.REDIS_PASSWORD
            
            # 添加 SSL 配置（如果需要）
            if settings.REDIS_SSL:
                connection_kwargs["ssl"] = True
                connection_kwargs["ssl_cert_reqs"] = "none"
            
            # 创建连接池
            self._connection_pool = ConnectionPool(**connection_kwargs)
            
            # 创建 Redis 客户端
            self._redis_client = Redis(connection_pool=self._connection_pool)
            
            logger.info(
                f"Redis 连接已建立: {settings.REDIS_HOST}:{settings.REDIS_PORT}/db{settings.REDIS_DB}"
            )
            
        except Exception as e:
            logger.error(f"Redis 连接失败: {e}")
            raise ExternalServiceError(
                "Redis 连接失败",
                details={
                    "host": settings.REDIS_HOST,
                    "port": settings.REDIS_PORT,
                    "error": str(e)
                }
            )
    
    async def ping(self) -> bool:
        """
        检查 Redis 连接是否正常
        
        Returns:
            连接是否正常
        """
        try:
            if self._redis_client is None:
                return False
            
            result = await self._redis_client.ping()
            return result is True
            
        except Exception as e:
            logger.error(f"Redis ping 失败: {e}")
            return False
    
    async def close(self) -> None:
        """
        关闭 Redis 连接
        """
        try:
            if self._redis_client:
                await self._redis_client.close()
            
            if self._connection_pool:
                await self._connection_pool.disconnect()
            
            self._redis_client = None
            self._connection_pool = None
            
            logger.info("Redis 连接已关闭")
            
        except Exception as e:
            logger.error(f"关闭 Redis 连接失败: {e}")
    
    async def reconnect(self) -> None:
        """
        重新连接 Redis
        """
        await self.close()
        self._connect()
    
    @property
    def client(self) -> Redis:
        """
        获取 Redis 客户端实例
        
        Returns:
            Redis 客户端实例
            
        Raises:
            ExternalServiceError: Redis 客户端未初始化
        """
        if self._redis_client is None:
            raise ExternalServiceError("Redis 客户端未初始化")
        return self._redis_client
    
    @asynccontextmanager
    async def get_connection(self):
        """
        获取 Redis 连接的上下文管理器
        
        Yields:
            Redis 连接
            
        Raises:
            ExternalServiceError: 获取连接失败
        """
        try:
            yield self.client
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis 连接异常: {e}")
            raise ExternalServiceError(
                "Redis 连接异常",
                details={"error": str(e)}
            )
        except Exception as e:
            logger.error(f"Redis 操作异常: {e}")
            raise ExternalServiceError(
                "Redis 操作异常",
                details={"error": str(e)}
            )
    
    async def execute_command(self, command: str, *args, **kwargs) -> Any:
        """
        执行 Redis 命令
        
        Args:
            command: Redis 命令
            *args: 命令参数
            **kwargs: 命令关键字参数
            
        Returns:
            命令执行结果
            
        Raises:
            ExternalServiceError: 命令执行失败
        """
        try:
            async with self.get_connection() as conn:
                result = await conn.execute_command(command, *args, **kwargs)
                return result
                
        except Exception as e:
            logger.error(f"Redis 命令执行失败: {command} - {e}")
            raise
    
    # ========== 基础键值操作 ==========
    
    async def set(
        self,
        key: str,
        value: Any,
        expire_seconds: Optional[int] = None,
        expire_milliseconds: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """
        设置键值对
        
        Args:
            key: 键名
            value: 值（支持字符串、数字、字典、列表等）
            expire_seconds: 过期时间（秒）
            expire_milliseconds: 过期时间（毫秒）
            nx: 仅当键不存在时设置
            xx: 仅当键存在时设置
            
        Returns:
            是否设置成功
        """
        try:
            # 序列化值
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, (int, float)):
                serialized_value = str(value)
            else:
                serialized_value = value
            
            async with self.get_connection() as conn:
                if expire_seconds:
                    if nx:
                        return await conn.set(
                            key, serialized_value, ex=expire_seconds, nx=True
                        )
                    elif xx:
                        return await conn.set(
                            key, serialized_value, ex=expire_seconds, xx=True
                        )
                    else:
                        return await conn.set(
                            key, serialized_value, ex=expire_seconds
                        )
                elif expire_milliseconds:
                    if nx:
                        return await conn.set(
                            key, serialized_value, px=expire_milliseconds, nx=True
                        )
                    elif xx:
                        return await conn.set(
                            key, serialized_value, px=expire_milliseconds, xx=True
                        )
                    else:
                        return await conn.set(
                            key, serialized_value, px=expire_milliseconds
                        )
                else:
                    if nx:
                        return await conn.set(key, serialized_value, nx=True)
                    elif xx:
                        return await conn.set(key, serialized_value, xx=True)
                    else:
                        return await conn.set(key, serialized_value)
                        
        except Exception as e:
            logger.error(f"Redis set 失败: {key} - {e}")
            raise
    
    async def get(self, key: str, default: Any = None) -> Any:
        """
        获取键值
        
        Args:
            key: 键名
            default: 默认值
            
        Returns:
            键值，如果键不存在则返回默认值
        """
        try:
            async with self.get_connection() as conn:
                value = await conn.get(key)
                
                if value is None:
                    return default
                
                # 尝试反序列化 JSON
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    # 如果不是 JSON，返回原始字符串
                    return value
                    
        except Exception as e:
            logger.error(f"Redis get 失败: {key} - {e}")
            return default
    
    async def delete(self, *keys: str) -> int:
        """
        删除键
        
        Args:
            *keys: 要删除的键名
            
        Returns:
            删除的键数量
        """
        try:
            async with self.get_connection() as conn:
                return await conn.delete(*keys)
                
        except Exception as e:
            logger.error(f"Redis delete 失败: {keys} - {e}")
            raise
    
    async def exists(self, *keys: str) -> int:
        """
        检查键是否存在
        
        Args:
            *keys: 要检查的键名
            
        Returns:
            存在的键数量
        """
        try:
            async with self.get_connection() as conn:
                return await conn.exists(*keys)
                
        except Exception as e:
            logger.error(f"Redis exists 失败: {keys} - {e}")
            raise
    
    async def expire(self, key: str, seconds: int) -> bool:
        """
        设置键的过期时间（秒）
        
        Args:
            key: 键名
            seconds: 过期秒数
            
        Returns:
            是否设置成功
        """
        try:
            async with self.get_connection() as conn:
                return await conn.expire(key, seconds)
                
        except Exception as e:
            logger.error(f"Redis expire 失败: {key} - {e}")
            raise
    
    async def ttl(self, key: str) -> int:
        """
        获取键的剩余生存时间（秒）
        
        Args:
            key: 键名
            
        Returns:
            剩余生存时间（秒），-1 表示没有设置过期时间，-2 表示键不存在
        """
        try:
            async with self.get_connection() as conn:
                return await conn.ttl(key)
                
        except Exception as e:
            logger.error(f"Redis ttl 失败: {key} - {e}")
            raise
    
    # ========== 哈希操作 ==========
    
    async def hset(self, key: str, field: str, value: Any) -> bool:
        """
        设置哈希字段值
        
        Args:
            key: 哈希键名
            field: 字段名
            value: 字段值
            
        Returns:
            是否设置成功
        """
        try:
            # 序列化值
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, (int, float)):
                serialized_value = str(value)
            else:
                serialized_value = value
            
            async with self.get_connection() as conn:
                return await conn.hset(key, field, serialized_value)
                
        except Exception as e:
            logger.error(f"Redis hset 失败: {key}.{field} - {e}")
            raise
    
    async def hget(self, key: str, field: str, default: Any = None) -> Any:
        """
        获取哈希字段值
        
        Args:
            key: 哈希键名
            field: 字段名
            default: 默认值
            
        Returns:
            字段值，如果字段不存在则返回默认值
        """
        try:
            async with self.get_connection() as conn:
                value = await conn.hget(key, field)
                
                if value is None:
                    return default
                
                # 尝试反序列化 JSON
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    # 如果不是 JSON，返回原始字符串
                    return value
                    
        except Exception as e:
            logger.error(f"Redis hget 失败: {key}.{field} - {e}")
            return default
    
    async def hgetall(self, key: str) -> Dict[str, Any]:
        """
        获取哈希所有字段值
        
        Args:
            key: 哈希键名
            
        Returns:
            字段名到字段值的映射
        """
        try:
            async with self.get_connection() as conn:
                result = await conn.hgetall(key)
                
                # 尝试反序列化 JSON 值
                deserialized = {}
                for field, value in result.items():
                    try:
                        deserialized[field] = json.loads(value)
                    except json.JSONDecodeError:
                        deserialized[field] = value
                
                return deserialized
                
        except Exception as e:
            logger.error(f"Redis hgetall 失败: {key} - {e}")
            raise
    
    async def hdel(self, key: str, *fields: str) -> int:
        """
        删除哈希字段
        
        Args:
            key: 哈希键名
            *fields: 要删除的字段名
            
        Returns:
            删除的字段数量
        """
        try:
            async with self.get_connection() as conn:
                return await conn.hdel(key, *fields)
                
        except Exception as e:
            logger.error(f"Redis hdel 失败: {key} - {e}")
            raise
    
    # ========== 列表操作 ==========
    
    async def lpush(self, key: str, *values: Any) -> int:
        """
        从列表左侧插入值
        
        Args:
            key: 列表键名
            *values: 要插入的值
            
        Returns:
            插入后列表的长度
        """
        try:
            # 序列化值
            serialized_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    serialized_values.append(json.dumps(value, ensure_ascii=False))
                elif isinstance(value, (int, float)):
                    serialized_values.append(str(value))
                else:
                    serialized_values.append(value)
            
            async with self.get_connection() as conn:
                return await conn.lpush(key, *serialized_values)
                
        except Exception as e:
            logger.error(f"Redis lpush 失败: {key} - {e}")
            raise
    
    async def rpush(self, key: str, *values: Any) -> int:
        """
        从列表右侧插入值
        
        Args:
            key: 列表键名
            *values: 要插入的值
            
        Returns:
            插入后列表的长度
        """
        try:
            # 序列化值
            serialized_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    serialized_values.append(json.dumps(value, ensure_ascii=False))
                elif isinstance(value, (int, float)):
                    serialized_values.append(str(value))
                else:
                    serialized_values.append(value)
            
            async with self.get_connection() as conn:
                return await conn.rpush(key, *serialized_values)
                
        except Exception as e:
            logger.error(f"Redis rpush 失败: {key} - {e}")
            raise
    
    async def lrange(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """
        获取列表指定范围内的值
        
        Args:
            key: 列表键名
            start: 起始索引
            end: 结束索引
            
        Returns:
            值列表
        """
        try:
            async with self.get_connection() as conn:
                values = await conn.lrange(key, start, end)
                
                # 尝试反序列化 JSON 值
                deserialized = []
                for value in values:
                    try:
                        deserialized.append(json.loads(value))
                    except json.JSONDecodeError:
                        deserialized.append(value)
                
                return deserialized
                
        except Exception as e:
            logger.error(f"Redis lrange 失败: {key} - {e}")
            raise
    
    async def ltrim(self, key: str, start: int, end: int) -> bool:
        """
        修剪列表，只保留指定范围内的元素
        
        Args:
            key: 列表键名
            start: 起始索引
            end: 结束索引
            
        Returns:
            是否修剪成功
        """
        try:
            async with self.get_connection() as conn:
                return await conn.ltrim(key, start, end)
                
        except Exception as e:
            logger.error(f"Redis ltrim 失败: {key} - {e}")
            raise
    
    # ========== 集合操作 ==========
    
    async def sadd(self, key: str, *members: Any) -> int:
        """
        向集合添加成员
        
        Args:
            key: 集合键名
            *members: 要添加的成员
            
        Returns:
            添加的成员数量
        """
        try:
            # 序列化成员
            serialized_members = []
            for member in members:
                if isinstance(member, (dict, list)):
                    serialized_members.append(json.dumps(member, ensure_ascii=False))
                elif isinstance(member, (int, float)):
                    serialized_members.append(str(member))
                else:
                    serialized_members.append(member)
            
            async with self.get_connection() as conn:
                return await conn.sadd(key, *serialized_members)
                
        except Exception as e:
            logger.error(f"Redis sadd 失败: {key} - {e}")
            raise
    
    async def smembers(self, key: str) -> List[Any]:
        """
        获取集合所有成员
        
        Args:
            key: 集合键名
            
        Returns:
            成员列表
        """
        try:
            async with self.get_connection() as conn:
                members = await conn.smembers(key)
                
                # 尝试反序列化 JSON 成员
                deserialized = []
                for member in members:
                    try:
                        deserialized.append(json.loads(member))
                    except json.JSONDecodeError:
                        deserialized.append(member)
                
                return deserialized
                
        except Exception as e:
            logger.error(f"Redis smembers 失败: {key} - {e}")
            raise
    
    async def sismember(self, key: str, member: Any) -> bool:
        """
        检查成员是否在集合中
        
        Args:
            key: 集合键名
            member: 要检查的成员
            
        Returns:
            成员是否在集合中
        """
        try:
            # 序列化成员
            if isinstance(member, (dict, list)):
                serialized_member = json.dumps(member, ensure_ascii=False)
            elif isinstance(member, (int, float)):
                serialized_member = str(member)
            else:
                serialized_member = member
            
            async with self.get_connection() as conn:
                return await conn.sismember(key, serialized_member)
                
        except Exception as e:
            logger.error(f"Redis sismember 失败: {key} - {e}")
            raise
    
    # ========== 发布订阅操作 ==========
    
    async def publish(self, channel: str, message: Any) -> int:
        """
        发布消息到频道
        
        Args:
            channel: 频道名
            message: 消息内容
            
        Returns:
            接收到消息的客户端数量
        """
        try:
            # 序列化消息
            if isinstance(message, (dict, list)):
                serialized_message = json.dumps(message, ensure_ascii=False)
            elif isinstance(message, (int, float)):
                serialized_message = str(message)
            else:
                serialized_message = message
            
            async with self.get_connection() as conn:
                return await conn.publish(channel, serialized_message)
                
        except Exception as e:
            logger.error(f"Redis publish 失败: {channel} - {e}")
            raise
    
    # ========== 批量操作 ==========
    
    async def pipeline(self):
        """
        获取管道对象，用于批量操作
        
        Returns:
            Redis 管道对象
        """
        try:
            async with self.get_connection() as conn:
                return conn.pipeline()
                
        except Exception as e:
            logger.error(f"Redis pipeline 创建失败: {e}")
            raise
    
    async def transaction(self, *args, **kwargs):
        """
        获取事务对象
        
        Returns:
            Redis 事务对象
        """
        try:
            async with self.get_connection() as conn:
                return conn.multi_exec(*args, **kwargs)
                
        except Exception as e:
            logger.error(f"Redis transaction 创建失败: {e}")
            raise


# 全局 Redis 客户端实例
redis_client = RedisClient()