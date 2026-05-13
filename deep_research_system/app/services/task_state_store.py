"""
任务状态存储模块
实现任务状态保存与查询，任务事件流记录
"""

import json
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.redis_client import redis_client
from app.core.logging import get_logger

logger = get_logger(__name__)


class TaskStatus(str, Enum):
    """
    任务状态枚举
    """
    PENDING = "pending"  # 等待中
    RUNNING = "running"  # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消
    TIMEOUT = "timeout"  # 超时


class TaskEventType(str, Enum):
    """
    任务事件类型枚举
    """
    CREATED = "created"  # 任务创建
    STARTED = "started"  # 任务开始
    PROGRESS = "progress"  # 进度更新
    STAGE_CHANGED = "stage_changed"  # 阶段变更
    AGENT_EXECUTED = "agent_executed"  # Agent 执行
    AGENT_COMPLETED = "agent_completed"  # Agent 完成
    AGENT_FAILED = "agent_failed"  # Agent 失败
    TOPOLOGY_STARTED = "topology_started"  # 拓扑开始
    TOPOLOGY_COMPLETED = "topology_completed"  # 拓扑完成
    RESULT_GENERATED = "result_generated"  # 结果生成
    ERROR = "error"  # 错误
    CANCELLED = "cancelled"  # 取消
    COMPLETED = "completed"  # 完成
    FAILED = "failed"  # 失败


class TaskEvent(BaseModel):
    """
    任务事件模型
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: TaskEventType
    task_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    data: Dict[str, Any] = Field(default_factory=dict)
    agent_name: Optional[str] = None
    stage_name: Optional[str] = None
    progress: Optional[int] = None  # 0-100
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    class Config:
        use_enum_values = True


class TaskState(BaseModel):
    """
    任务状态模型
    """
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: int = 0  # 0-100
    current_stage: Optional[str] = None
    current_agent: Optional[str] = None
    topology_name: Optional[str] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    event_count: int = 0
    last_event_id: Optional[str] = None
    
    class Config:
        use_enum_values = True


class TaskStateStore:
    """
    任务状态存储类
    实现任务状态保存与查询，任务事件流记录
    """
    
    def __init__(self, namespace: str = "research"):
        """
        初始化任务状态存储
        
        Args:
            namespace: 命名空间，用于区分不同类型的任务
        """
        self.namespace = namespace
        self.state_ttl = 86400 * 7  # 任务状态保存7天
        self.events_ttl = 86400 * 3  # 任务事件保存3天
        
        logger.info(f"任务状态存储初始化完成，命名空间: {namespace}")
    
    def _generate_state_key(self, task_id: str) -> str:
        """
        生成任务状态键
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态键
        """
        return f"{self.namespace}:task:{task_id}:state"
    
    def _generate_events_key(self, task_id: str) -> str:
        """
        生成任务事件键
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务事件键
        """
        return f"{self.namespace}:task:{task_id}:events"
    
    def _generate_task_index_key(self) -> str:
        """
        生成任务索引键
        
        Returns:
            任务索引键
        """
        return f"{self.namespace}:tasks:index"
    
    async def create_task(
        self,
        task_id: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        topology_name: Optional[str] = None
    ) -> TaskState:
        """
        创建新任务
        
        Args:
            task_id: 任务ID，如果为 None 则自动生成
            input_data: 输入数据
            metadata: 元数据
            topology_name: 拓扑名称
            
        Returns:
            任务状态
        """
        try:
            # 生成任务ID
            if task_id is None:
                task_id = str(uuid.uuid4())
            
            # 创建任务状态
            task_state = TaskState(
                task_id=task_id,
                input_data=input_data or {},
                metadata=metadata or {},
                topology_name=topology_name,
            )
            
            # 保存任务状态
            await self.save_task_state(task_state)
            
            # 创建任务创建事件
            create_event = TaskEvent(
                event_type=TaskEventType.CREATED,
                task_id=task_id,
                data={
                    "input_data": input_data or {},
                    "metadata": metadata or {},
                    "topology_name": topology_name,
                }
            )
            
            # 记录事件
            await self.record_event(create_event)
            
            # 添加到任务索引
            await self._add_to_task_index(task_id)
            
            logger.info(f"任务创建成功: {task_id}")
            
            return task_state
            
        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            raise
    
    async def save_task_state(self, task_state: TaskState) -> bool:
        """
        保存任务状态
        
        Args:
            task_state: 任务状态
            
        Returns:
            是否保存成功
        """
        try:
            # 更新更新时间
            task_state.updated_at = datetime.utcnow().isoformat() + "Z"
            
            # 生成状态键
            state_key = self._generate_state_key(task_state.task_id)
            
            # 保存到 Redis
            success = await redis_client.set(
                state_key,
                task_state.dict(),
                expire_seconds=self.state_ttl
            )
            
            if success:
                logger.debug(f"任务状态保存成功: {task_state.task_id}")
            else:
                logger.warning(f"任务状态保存失败: {task_state.task_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"保存任务状态失败: {task_state.task_id} - {e}")
            return False
    
    async def get_task_state(self, task_id: str) -> Optional[TaskState]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态，如果不存在则返回 None
        """
        try:
            # 生成状态键
            state_key = self._generate_state_key(task_id)
            
            # 从 Redis 获取
            state_data = await redis_client.get(state_key)
            
            if state_data is None:
                logger.debug(f"任务状态不存在: {task_id}")
                return None
            
            # 转换为 TaskState 对象
            task_state = TaskState(**state_data)
            
            logger.debug(f"获取任务状态成功: {task_id}")
            
            return task_state
            
        except Exception as e:
            logger.error(f"获取任务状态失败: {task_id} - {e}")
            return None
    
    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: Optional[int] = None,
        current_stage: Optional[str] = None,
        current_agent: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[Dict[str, Any]] = None
    ) -> Optional[TaskState]:
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            progress: 进度（0-100）
            current_stage: 当前阶段
            current_agent: 当前 Agent
            result: 结果
            error: 错误信息
            
        Returns:
            更新后的任务状态，如果任务不存在则返回 None
        """
        try:
            # 获取当前任务状态
            task_state = await self.get_task_state(task_id)
            
            if task_state is None:
                logger.warning(f"任务不存在，无法更新状态: {task_id}")
                return None
            
            # 更新状态
            task_state.status = status
            task_state.updated_at = datetime.utcnow().isoformat() + "Z"
            
            # 更新开始时间（如果状态变为 RUNNING）
            if status == TaskStatus.RUNNING and task_state.started_at is None:
                task_state.started_at = task_state.updated_at
            
            # 更新完成时间（如果状态变为 COMPLETED 或 FAILED）
            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.TIMEOUT]:
                if task_state.completed_at is None:
                    task_state.completed_at = task_state.updated_at
            
            # 更新其他字段
            if progress is not None:
                task_state.progress = progress
            
            if current_stage is not None:
                task_state.current_stage = current_stage
            
            if current_agent is not None:
                task_state.current_agent = current_agent
            
            if result is not None:
                task_state.result = result
            
            if error is not None:
                task_state.error = error
            
            # 保存更新后的状态
            success = await self.save_task_state(task_state)
            
            if success:
                logger.debug(f"任务状态更新成功: {task_id} -> {status}")
            else:
                logger.warning(f"任务状态更新失败: {task_id}")
            
            return task_state if success else None
            
        except Exception as e:
            logger.error(f"更新任务状态失败: {task_id} - {e}")
            return None
    
    async def record_event(self, event: TaskEvent) -> bool:
        """
        记录任务事件
        
        Args:
            event: 任务事件
            
        Returns:
            是否记录成功
        """
        try:
            # 生成事件键
            events_key = self._generate_events_key(event.task_id)
            
            # 将事件转换为字典
            event_dict = event.dict()
            
            # 将事件添加到列表
            success = await redis_client.rpush(events_key, event_dict)
            
            if success:
                # 设置过期时间
                await redis_client.expire(events_key, self.events_ttl)
                
                # 更新任务状态中的事件计数
                task_state = await self.get_task_state(event.task_id)
                if task_state:
                    task_state.event_count += 1
                    task_state.last_event_id = event.event_id
                    await self.save_task_state(task_state)
                
                logger.debug(f"任务事件记录成功: {event.task_id} - {event.event_type}")
            else:
                logger.warning(f"任务事件记录失败: {event.task_id} - {event.event_type}")
            
            return bool(success)
            
        except Exception as e:
            logger.error(f"记录任务事件失败: {event.task_id} - {e}")
            return False
    
    async def get_task_events(
        self,
        task_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        event_type: Optional[TaskEventType] = None
    ) -> List[TaskEvent]:
        """
        获取任务事件
        
        Args:
            task_id: 任务ID
            limit: 限制返回的事件数量
            offset: 偏移量
            event_type: 事件类型过滤
            
        Returns:
            任务事件列表
        """
        try:
            # 生成事件键
            events_key = self._generate_events_key(task_id)
            
            # 获取所有事件
            events_data = await redis_client.lrange(events_key, 0, -1)
            
            if not events_data:
                return []
            
            # 转换为 TaskEvent 对象
            events = []
            for event_data in events_data:
                try:
                    event = TaskEvent(**event_data)
                    
                    # 过滤事件类型
                    if event_type and event.event_type != event_type:
                        continue
                    
                    events.append(event)
                except Exception as e:
                    logger.warning(f"解析任务事件失败: {e}")
            
            # 应用偏移和限制
            if offset > 0:
                events = events[offset:]
            
            if limit is not None:
                events = events[:limit]
            
            logger.debug(f"获取任务事件成功: {task_id} ({len(events)} 个事件)")
            
            return events
            
        except Exception as e:
            logger.error(f"获取任务事件失败: {task_id} - {e}")
            return []
    
    async def get_latest_events(
        self,
        task_id: str,
        count: int = 10,
        event_type: Optional[TaskEventType] = None
    ) -> List[TaskEvent]:
        """
        获取最新的事件
        
        Args:
            task_id: 任务ID
            count: 事件数量
            event_type: 事件类型过滤
            
        Returns:
            最新的事件列表
        """
        try:
            # 生成事件键
            events_key = self._generate_events_key(task_id)
            
            # 获取最新的事件（从列表末尾开始）
            events_data = await redis_client.lrange(events_key, -count, -1)
            
            if not events_data:
                return []
            
            # 转换为 TaskEvent 对象
            events = []
            for event_data in events_data:
                try:
                    event = TaskEvent(**event_data)
                    
                    # 过滤事件类型
                    if event_type and event.event_type != event_type:
                        continue
                    
                    events.append(event)
                except Exception as e:
                    logger.warning(f"解析任务事件失败: {e}")
            
            logger.debug(f"获取最新任务事件成功: {task_id} ({len(events)} 个事件)")
            
            return events
            
        except Exception as e:
            logger.error(f"获取最新任务事件失败: {task_id} - {e}")
            return []
    
    async def record_agent_execution(
        self,
        task_id: str,
        agent_name: str,
        stage_name: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        记录 Agent 执行事件
        
        Args:
            task_id: 任务ID
            agent_name: Agent 名称
            stage_name: 阶段名称
            input_data: 输入数据
            output_data: 输出数据
            duration_ms: 执行时长（毫秒）
            success: 是否成功
            error_message: 错误信息
            error_details: 错误详情
            
        Returns:
            是否记录成功
        """
        try:
            # 确定事件类型
            event_type = TaskEventType.AGENT_COMPLETED if success else TaskEventType.AGENT_FAILED
            
            # 构建事件数据
            event_data = {
                "agent_name": agent_name,
                "stage_name": stage_name,
                "input_data": input_data or {},
                "output_data": output_data or {},
                "duration_ms": duration_ms,
                "success": success,
            }
            
            if not success:
                event_data["error_message"] = error_message
                event_data["error_details"] = error_details
            
            # 创建事件
            event = TaskEvent(
                event_type=event_type,
                task_id=task_id,
                agent_name=agent_name,
                stage_name=stage_name,
                data=event_data,
                error_message=error_message,
                error_details=error_details,
            )
            
            # 记录事件
            return await self.record_event(event)
            
        except Exception as e:
            logger.error(f"记录 Agent 执行事件失败: {task_id} - {agent_name} - {e}")
            return False
    
    async def record_progress_update(
        self,
        task_id: str,
        progress: int,
        stage_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        message: Optional[str] = None
    ) -> bool:
        """
        记录进度更新事件
        
        Args:
            task_id: 任务ID
            progress: 进度（0-100）
            stage_name: 阶段名称
            agent_name: Agent 名称
            message: 进度消息
            
        Returns:
            是否记录成功
        """
        try:
            # 构建事件数据
            event_data = {
                "progress": progress,
                "stage_name": stage_name,
                "agent_name": agent_name,
                "message": message,
            }
            
            # 创建事件
            event = TaskEvent(
                event_type=TaskEventType.PROGRESS,
                task_id=task_id,
                stage_name=stage_name,
                agent_name=agent_name,
                progress=progress,
                data=event_data,
            )
            
            # 记录事件
            success = await self.record_event(event)
            
            # 同时更新任务状态
            if success:
                await self.update_task_status(
                    task_id=task_id,
                    status=TaskStatus.RUNNING,
                    progress=progress,
                    current_stage=stage_name,
                    current_agent=agent_name,
                )
            
            return success
            
        except Exception as e:
            logger.error(f"记录进度更新事件失败: {task_id} - {e}")
            return False
    
    async def record_stage_change(
        self,
        task_id: str,
        stage_name: str,
        previous_stage: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> bool:
        """
        记录阶段变更事件
        
        Args:
            task_id: 任务ID
            stage_name: 新阶段名称
            previous_stage: 前一阶段名称
            agent_name: Agent 名称
            
        Returns:
            是否记录成功
        """
        try:
            # 构建事件数据
            event_data = {
                "stage_name": stage_name,
                "previous_stage": previous_stage,
                "agent_name": agent_name,
            }
            
            # 创建事件
            event = TaskEvent(
                event_type=TaskEventType.STAGE_CHANGED,
                task_id=task_id,
                stage_name=stage_name,
                agent_name=agent_name,
                data=event_data,
            )
            
            # 记录事件
            success = await self.record_event(event)
            
            # 同时更新任务状态
            if success:
                await self.update_task_status(
                    task_id=task_id,
                    status=TaskStatus.RUNNING,
                    current_stage=stage_name,
                    current_agent=agent_name,
                )
            
            return success
            
        except Exception as e:
            logger.error(f"记录阶段变更事件失败: {task_id} - {e}")
            return False
    
    async def delete_task(self, task_id: str) -> bool:
        """
        删除任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否删除成功
        """
        try:
            # 删除任务状态
            state_key = self._generate_state_key(task_id)
            state_deleted = await redis_client.delete(state_key)
            
            # 删除任务事件
            events_key = self._generate_events_key(task_id)
            events_deleted = await redis_client.delete(events_key)
            
            # 从任务索引中移除
            await self._remove_from_task_index(task_id)
            
            success = state_deleted > 0 or events_deleted > 0
            
            if success:
                logger.info(f"任务删除成功: {task_id}")
            else:
                logger.debug(f"任务不存在或已删除: {task_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"删除任务失败: {task_id} - {e}")
            return False
    
    async def cleanup_old_tasks(self, days: int = 7) -> int:
        """
        清理旧任务
        
        Args:
            days: 保留天数
            
        Returns:
            清理的任务数量
        """
        try:
            # 获取所有任务ID
            task_ids = await self._get_all_task_ids()
            
            if not task_ids:
                return 0
            
            # 计算截止时间
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            cutoff_timestamp = cutoff_time.isoformat() + "Z"
            
            cleaned_count = 0
            
            # 检查每个任务
            for task_id in task_ids:
                task_state = await self.get_task_state(task_id)
                
                if task_state is None:
                    # 任务状态不存在，删除相关键
                    await self.delete_task(task_id)
                    cleaned_count += 1
                    continue
                
                # 检查任务创建时间
                if task_state.created_at < cutoff_timestamp:
                    # 任务已过期，删除它
                    await self.delete_task(task_id)
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"清理了 {cleaned_count} 个旧任务（保留 {days} 天）")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理旧任务失败: {e}")
            return 0
    
    async def get_task_stats(self) -> Dict[str, Any]:
        """
        获取任务统计信息
        
        Returns:
            任务统计信息字典
        """
        try:
            # 获取所有任务ID
            task_ids = await self._get_all_task_ids()
            
            # 统计各状态的任务数量
            status_counts = {status.value: 0 for status in TaskStatus}
            total_tasks = len(task_ids)
            
            # 统计每个任务的状态
            for task_id in task_ids:
                task_state = await self.get_task_state(task_id)
                if task_state:
                    status_counts[task_state.status] += 1
            
            # 构建统计信息
            stats = {
                "namespace": self.namespace,
                "total_tasks": total_tasks,
                "status_counts": status_counts,
                "active_tasks": status_counts[TaskStatus.RUNNING.value] + status_counts[TaskStatus.PENDING.value],
                "completed_tasks": status_counts[TaskStatus.COMPLETED.value],
                "failed_tasks": status_counts[TaskStatus.FAILED.value],
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取任务统计信息失败: {e}")
            return {
                "namespace": self.namespace,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
    
    async def _add_to_task_index(self, task_id: str) -> bool:
        """
        添加到任务索引
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否添加成功
        """
        try:
            index_key = self._generate_task_index_key()
            success = await redis_client.sadd(index_key, task_id)
            
            # 设置过期时间（比任务状态长一些）
            await redis_client.expire(index_key, self.state_ttl + 86400)
            
            return bool(success)
            
        except Exception as e:
            logger.error(f"添加到任务索引失败: {task_id} - {e}")
            return False
    
    async def _remove_from_task_index(self, task_id: str) -> bool:
        """
        从任务索引中移除
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否移除成功
        """
        try:
            index_key = self._generate_task_index_key()
            removed = await redis_client.srem(index_key, task_id)
            return removed > 0
            
        except Exception as e:
            logger.error(f"从任务索引中移除失败: {task_id} - {e}")
            return False
    
    async def _get_all_task_ids(self) -> List[str]:
        """
        获取所有任务ID
        
        Returns:
            任务ID列表
        """
        try:
            index_key = self._generate_task_index_key()
            task_ids = await redis_client.smembers(index_key)
            return list(task_ids)
            
        except Exception as e:
            logger.error(f"获取所有任务ID失败: {e}")
            return []
    
    async def search_tasks(
        self,
        status: Optional[TaskStatus] = None,
        topology_name: Optional[str] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TaskState]:
        """
        搜索任务
        
        Args:
            status: 状态过滤
            topology_name: 拓扑名称过滤
            created_after: 创建时间之后
            created_before: 创建时间之前
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            任务状态列表
        """
        try:
            # 获取所有任务ID
            task_ids = await self._get_all_task_ids()
            
            if not task_ids:
                return []
            
            # 过滤任务
            filtered_tasks = []
            
            for task_id in task_ids:
                task_state = await self.get_task_state(task_id)
                
                if task_state is None:
                    continue
                
                # 状态过滤
                if status and task_state.status != status:
                    continue
                
                # 拓扑名称过滤
                if topology_name and task_state.topology_name != topology_name:
                    continue
                
                # 创建时间过滤
                if created_after and task_state.created_at < created_after:
                    continue
                
                if created_before and task_state.created_at > created_before:
                    continue
                
                filtered_tasks.append(task_state)
            
            # 按创建时间排序（最新的在前）
            filtered_tasks.sort(key=lambda x: x.created_at, reverse=True)
            
            # 应用偏移和限制
            if offset > 0:
                filtered_tasks = filtered_tasks[offset:]
            
            if limit > 0:
                filtered_tasks = filtered_tasks[:limit]
            
            logger.debug(f"搜索任务完成: 找到 {len(filtered_tasks)} 个任务")
            
            return filtered_tasks
            
        except Exception as e:
            logger.error(f"搜索任务失败: {e}")
            return []


# 全局任务状态存储实例
task_state_store = TaskStateStore()