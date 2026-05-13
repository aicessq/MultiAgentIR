"""
缓存服务模块
实现查询缓存功能，支持缓存过期策略
"""

import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.redis_client import redis_client
from app.core.logging import get_logger

logger = get_logger(__name__)


class CacheService:
    """
    缓存服务类
    提供查询缓存功能，支持缓存过期策略
    """
    
    def __init__(self, namespace: str = "research"):
        """
        初始化缓存服务
        
        Args:
            namespace: 缓存命名空间，用于区分不同类型的缓存
        """
        self.namespace = namespace
        self.default_ttl = settings.CACHE_TTL
        self.search_cache_ttl = settings.SEARCH_CACHE_TTL
        self.model_cache_ttl = settings.MODEL_CACHE_TTL
        
        logger.info(f"缓存服务初始化完成，命名空间: {namespace}")
    
    def _generate_key(self, cache_type: str, identifier: str) -> str:
        """
        生成缓存键
        
        Args:
            cache_type: 缓存类型，如 "query", "search", "model"
            identifier: 标识符，如查询哈希、搜索关键词等
            
        Returns:
            完整的缓存键
        """
        # 清理标识符中的特殊字符
        clean_identifier = str(identifier).replace(":", "_").replace(" ", "_")
        return f"{self.namespace}:{cache_type}:{clean_identifier}"
    
    def _generate_query_hash(self, query: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        生成查询哈希
        
        Args:
            query: 查询字符串
            params: 查询参数
            
        Returns:
            查询哈希值
        """
        # 构建哈希内容
        hash_content = query
        
        if params:
            # 将参数排序以确保一致性
            sorted_params = json.dumps(params, sort_keys=True, ensure_ascii=False)
            hash_content += sorted_params
        
        # 生成 MD5 哈希
        return hashlib.md5(hash_content.encode('utf-8')).hexdigest()
    
    async def cache_query(
        self,
        query: str,
        result: Any,
        params: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
        cache_type: str = "query"
    ) -> bool:
        """
        缓存查询结果
        
        Args:
            query: 查询字符串
            result: 查询结果
            params: 查询参数
            ttl: 缓存过期时间（秒），如果为 None 则使用默认值
            cache_type: 缓存类型
            
        Returns:
            是否缓存成功
        """
        try:
            # 生成查询哈希和缓存键
            query_hash = self._generate_query_hash(query, params)
            cache_key = self._generate_key(cache_type, query_hash)
            
            # 确定 TTL
            if ttl is None:
                if cache_type == "search":
                    ttl = self.search_cache_ttl
                elif cache_type == "model":
                    ttl = self.model_cache_ttl
                else:
                    ttl = self.default_ttl
            
            # 构建缓存数据
            cache_data = {
                "query": query,
                "params": params or {},
                "result": result,
                "cached_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(seconds=ttl)).isoformat(),
                "query_hash": query_hash,
                "cache_type": cache_type,
            }
            
            # 缓存数据
            success = await redis_client.set(cache_key, cache_data, expire_seconds=ttl)
            
            if success:
                logger.debug(f"查询缓存成功: {cache_key} (TTL: {ttl}s)")
            else:
                logger.warning(f"查询缓存失败: {cache_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"缓存查询失败: {query} - {e}")
            return False
    
    async def get_cached_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        cache_type: str = "query"
    ) -> Optional[Any]:
        """
        获取缓存的查询结果
        
        Args:
            query: 查询字符串
            params: 查询参数
            cache_type: 缓存类型
            
        Returns:
            缓存的查询结果，如果未找到或已过期则返回 None
        """
        try:
            # 生成查询哈希和缓存键
            query_hash = self._generate_query_hash(query, params)
            cache_key = self._generate_key(cache_type, query_hash)
            
            # 获取缓存数据
            cache_data = await redis_client.get(cache_key)
            
            if cache_data is None:
                logger.debug(f"缓存未命中: {cache_key}")
                return None
            
            # 检查缓存是否过期
            expires_at_str = cache_data.get("expires_at")
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str.replace("Z", ""))
                if datetime.utcnow() > expires_at:
                    # 缓存已过期，删除它
                    await redis_client.delete(cache_key)
                    logger.debug(f"缓存已过期: {cache_key}")
                    return None
            
            logger.debug(f"缓存命中: {cache_key}")
            return cache_data.get("result")
            
        except Exception as e:
            logger.error(f"获取缓存查询失败: {query} - {e}")
            return None
    
    async def cache_search_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        search_params: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        缓存搜索结果
        
        Args:
            query: 搜索查询
            results: 搜索结果列表
            search_params: 搜索参数
            ttl: 缓存过期时间（秒）
            
        Returns:
            是否缓存成功
        """
        try:
            # 构建搜索结果数据
            search_data = {
                "query": query,
                "params": search_params or {},
                "results": results,
                "result_count": len(results),
                "cached_at": datetime.utcnow().isoformat(),
            }
            
            # 缓存搜索结果
            success = await self.cache_query(
                query=query,
                result=search_data,
                params=search_params,
                ttl=ttl or self.search_cache_ttl,
                cache_type="search"
            )
            
            if success:
                logger.info(f"搜索结果缓存成功: {query} ({len(results)} 条结果)")
            
            return success
            
        except Exception as e:
            logger.error(f"缓存搜索结果失败: {query} - {e}")
            return False
    
    async def get_cached_search_results(
        self,
        query: str,
        search_params: Optional[Dict[str, Any]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        获取缓存的搜索结果
        
        Args:
            query: 搜索查询
            search_params: 搜索参数
            
        Returns:
            缓存的搜索结果列表，如果未找到或已过期则返回 None
        """
        try:
            # 获取缓存数据
            cache_data = await self.get_cached_query(
                query=query,
                params=search_params,
                cache_type="search"
            )
            
            if cache_data is None:
                return None
            
            # 返回搜索结果
            return cache_data.get("results", [])
            
        except Exception as e:
            logger.error(f"获取缓存搜索结果失败: {query} - {e}")
            return None
    
    async def cache_model_response(
        self,
        model_name: str,
        prompt: str,
        response: Any,
        model_params: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        缓存模型响应
        
        Args:
            model_name: 模型名称
            prompt: 提示词
            response: 模型响应
            model_params: 模型参数
            ttl: 缓存过期时间（秒）
            
        Returns:
            是否缓存成功
        """
        try:
            # 构建模型响应数据
            model_response_data = {
                "model_name": model_name,
                "prompt": prompt,
                "params": model_params or {},
                "response": response,
                "cached_at": datetime.utcnow().isoformat(),
            }
            
            # 生成缓存标识符
            cache_identifier = f"{model_name}:{hashlib.md5(prompt.encode('utf-8')).hexdigest()}"
            
            # 缓存模型响应
            cache_key = self._generate_key("model", cache_identifier)
            success = await redis_client.set(
                cache_key,
                model_response_data,
                expire_seconds=ttl or self.model_cache_ttl
            )
            
            if success:
                logger.debug(f"模型响应缓存成功: {cache_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"缓存模型响应失败: {model_name} - {e}")
            return False
    
    async def get_cached_model_response(
        self,
        model_name: str,
        prompt: str,
        model_params: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        获取缓存的模型响应
        
        Args:
            model_name: 模型名称
            prompt: 提示词
            model_params: 模型参数
            
        Returns:
            缓存的模型响应，如果未找到或已过期则返回 None
        """
        try:
            # 生成缓存标识符
            cache_identifier = f"{model_name}:{hashlib.md5(prompt.encode('utf-8')).hexdigest()}"
            cache_key = self._generate_key("model", cache_identifier)
            
            # 获取缓存数据
            cache_data = await redis_client.get(cache_key)
            
            if cache_data is None:
                return None
            
            # 检查参数是否匹配
            cached_params = cache_data.get("params", {})
            if model_params and cached_params != model_params:
                logger.debug(f"模型参数不匹配: {cache_key}")
                return None
            
            logger.debug(f"模型响应缓存命中: {cache_key}")
            return cache_data.get("response")
            
        except Exception as e:
            logger.error(f"获取缓存模型响应失败: {model_name} - {e}")
            return None
    
    async def cache_agent_output(
        self,
        agent_name: str,
        input_data: Dict[str, Any],
        output_data: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        缓存 Agent 输出
        
        Args:
            agent_name: Agent 名称
            input_data: 输入数据
            output_data: 输出数据
            ttl: 缓存过期时间（秒）
            
        Returns:
            是否缓存成功
        """
        try:
            # 生成输入数据哈希
            input_hash = hashlib.md5(
                json.dumps(input_data, sort_keys=True, ensure_ascii=False).encode('utf-8')
            ).hexdigest()
            
            # 构建缓存数据
            cache_data = {
                "agent_name": agent_name,
                "input_data": input_data,
                "output_data": output_data,
                "cached_at": datetime.utcnow().isoformat(),
                "input_hash": input_hash,
            }
            
            # 生成缓存键
            cache_key = self._generate_key("agent", f"{agent_name}:{input_hash}")
            
            # 缓存数据
            success = await redis_client.set(
                cache_key,
                cache_data,
                expire_seconds=ttl or self.default_ttl
            )
            
            if success:
                logger.debug(f"Agent 输出缓存成功: {cache_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"缓存 Agent 输出失败: {agent_name} - {e}")
            return False
    
    async def get_cached_agent_output(
        self,
        agent_name: str,
        input_data: Dict[str, Any]
    ) -> Optional[Any]:
        """
        获取缓存的 Agent 输出
        
        Args:
            agent_name: Agent 名称
            input_data: 输入数据
            
        Returns:
            缓存的 Agent 输出，如果未找到或已过期则返回 None
        """
        try:
            # 生成输入数据哈希
            input_hash = hashlib.md5(
                json.dumps(input_data, sort_keys=True, ensure_ascii=False).encode('utf-8')
            ).hexdigest()
            
            # 生成缓存键
            cache_key = self._generate_key("agent", f"{agent_name}:{input_hash}")
            
            # 获取缓存数据
            cache_data = await redis_client.get(cache_key)
            
            if cache_data is None:
                return None
            
            logger.debug(f"Agent 输出缓存命中: {cache_key}")
            return cache_data.get("output_data")
            
        except Exception as e:
            logger.error(f"获取缓存 Agent 输出失败: {agent_name} - {e}")
            return None
    
    async def delete_cache(self, cache_type: str, identifier: str) -> bool:
        """
        删除缓存
        
        Args:
            cache_type: 缓存类型
            identifier: 缓存标识符
            
        Returns:
            是否删除成功
        """
        try:
            cache_key = self._generate_key(cache_type, identifier)
            deleted_count = await redis_client.delete(cache_key)
            
            success = deleted_count > 0
            if success:
                logger.debug(f"缓存删除成功: {cache_key}")
            else:
                logger.debug(f"缓存未找到: {cache_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"删除缓存失败: {cache_type}:{identifier} - {e}")
            return False
    
    async def clear_namespace(self, cache_type: Optional[str] = None) -> int:
        """
        清除命名空间下的所有缓存
        
        Args:
            cache_type: 缓存类型，如果为 None 则清除所有类型
            
        Returns:
            删除的缓存数量
        """
        try:
            # 注意：在生产环境中，应使用 SCAN 命令而不是 KEYS 命令
            # 这里使用 KEYS 命令是因为缓存键数量通常不会太大
            
            if cache_type:
                pattern = f"{self.namespace}:{cache_type}:*"
            else:
                pattern = f"{self.namespace}:*"
            
            # 获取匹配的键
            async with redis_client.get_connection() as conn:
                keys = await conn.keys(pattern)
                
                if not keys:
                    logger.debug(f"没有找到匹配的缓存键: {pattern}")
                    return 0
                
                # 删除键
                deleted_count = await conn.delete(*keys)
                logger.info(f"清除缓存完成: 删除了 {deleted_count} 个键 (模式: {pattern})")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息字典
        """
        try:
            stats = {
                "namespace": self.namespace,
                "default_ttl": self.default_ttl,
                "search_cache_ttl": self.search_cache_ttl,
                "model_cache_ttl": self.model_cache_ttl,
                "cache_types": {},
                "total_keys": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            # 统计各缓存类型的键数量
            cache_types = ["query", "search", "model", "agent"]
            
            for cache_type in cache_types:
                pattern = f"{self.namespace}:{cache_type}:*"
                
                async with redis_client.get_connection() as conn:
                    keys = await conn.keys(pattern)
                    stats["cache_types"][cache_type] = len(keys)
                    stats["total_keys"] += len(keys)
            
            return stats
            
        except Exception as e:
            logger.error(f"获取缓存统计信息失败: {e}")
            return {
                "namespace": self.namespace,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    async def cleanup_expired_cache(self) -> int:
        """
        清理过期缓存
        
        Returns:
            清理的缓存数量
        """
        # Redis 会自动清理过期缓存
        # 这个方法主要用于统计和日志记录
        try:
            stats_before = await self.get_cache_stats()
            
            # 等待 Redis 清理过期键
            await asyncio.sleep(1)
            
            stats_after = await self.get_cache_stats()
            
            cleaned_count = stats_before.get("total_keys", 0) - stats_after.get("total_keys", 0)
            
            if cleaned_count > 0:
                logger.info(f"清理了 {cleaned_count} 个过期缓存")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")
            return 0


# 全局缓存服务实例
cache_service = CacheService()