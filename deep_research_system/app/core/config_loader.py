"""
配置加载器模块
加载和验证 YAML 配置文件
"""

import os
import yaml
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.errors import ConfigurationError
from app.core.logging import get_logger

logger = get_logger(__name__)


class ModelSpec(BaseModel):
    """
    模型规格配置模型
    对应 config/models.yaml 中的模型定义
    """
    
    name: str
    provider: str
    api_base_env: str
    api_key_env: str
    model_name_env: str
    capabilities: List[str]
    cost_tier: str
    latency_tier: str
    context_window: int
    max_tokens_env: str
    temperature_env: str
    enabled: bool = True
    description: Optional[str] = None
    
    class Config:
        extra = "forbid"  # 禁止额外字段


class AgentConfig(BaseModel):
    """
    Agent 配置模型
    对应 config/agents.yaml 中的 Agent 定义
    """
    
    name: str
    description: str
    required_capabilities: List[str]
    preferred_capabilities: List[str] = []
    preferred_cost_tier: str
    prompt_template: str
    output_schema: str
    max_retries: int = 3
    timeout_seconds: int = 30
    max_sources_per_query: Optional[int] = None
    min_evidence_per_source: Optional[int] = None
    max_evidence_per_source: Optional[int] = None
    allow_research_loop: bool = False
    max_research_loops: int = 0
    default_template: Optional[str] = None
    
    class Config:
        extra = "forbid"


class TopologyConfig(BaseModel):
    """
    拓扑配置模型
    对应 config/topology.yaml 中的拓扑定义
    """
    
    name: str
    description: str
    flow: str
    max_sub_questions: Optional[int] = None
    max_sources_per_sub_question: Optional[int] = None
    allow_critic_research_loop: bool = False
    max_research_loops: int = 0
    max_concurrent_searchers: Optional[int] = None
    max_concurrent_readers: Optional[int] = None
    searcher_timeout_seconds: Optional[int] = None
    reader_timeout_seconds: Optional[int] = None
    min_sources_per_sub_question: Optional[int] = None
    min_evidence_per_source: Optional[int] = None
    require_citations: bool = True
    default_report_sections: Optional[List[str]] = None
    
    class Config:
        extra = "forbid"


class ConfigManager:
    """
    配置管理器
    负责加载、验证和管理所有配置文件
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录，默认为项目根目录下的 config 目录
        """
        if config_dir is None:
            self.config_dir = Path(__file__).parent.parent.parent / "config"
        else:
            self.config_dir = Path(config_dir)
        
        # 配置文件路径
        self.models_config_path = self.config_dir / "models.yaml"
        self.agents_config_path = self.config_dir / "agents.yaml"
        self.topology_config_path = self.config_dir / "topology.yaml"
        
        # 配置缓存
        self._models_config: Optional[Dict[str, Any]] = None
        self._agents_config: Optional[Dict[str, Any]] = None
        self._topology_config: Optional[Dict[str, Any]] = None
        
        # 最后修改时间，用于热重载
        self._last_modified: Dict[str, float] = {}
        
        # 配置验证模型
        self._model_specs: List[ModelSpec] = []
        self._agent_configs: Dict[str, AgentConfig] = {}
        self._topology_configs: Dict[str, TopologyConfig] = {}
        
        logger.info(f"配置管理器初始化完成，配置目录: {self.config_dir}")
    
    def load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """
        加载 YAML 文件
        
        Args:
            file_path: YAML 文件路径
            
        Returns:
            解析后的配置字典
            
        Raises:
            ConfigurationError: 文件不存在或解析失败
        """
        if not file_path.exists():
            raise ConfigurationError(
                f"配置文件不存在: {file_path}",
                details={"file_path": str(file_path)}
            )
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                config = yaml.safe_load(content)
            
            if config is None:
                config = {}
            
            # 记录最后修改时间
            self._last_modified[str(file_path)] = file_path.stat().st_mtime
            
            logger.debug(f"成功加载配置文件: {file_path}")
            return config
            
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"YAML 解析失败: {file_path}",
                details={"file_path": str(file_path), "error": str(e)}
            )
        except Exception as e:
            raise ConfigurationError(
                f"加载配置文件失败: {file_path}",
                details={"file_path": str(file_path), "error": str(e)}
            )
    
    def load_models_config(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        加载模型配置
        
        Args:
            force_reload: 是否强制重新加载
            
        Returns:
            模型配置字典
        """
        if self._models_config is None or force_reload:
            self._models_config = self.load_yaml_file(self.models_config_path)
            self._validate_models_config()
        
        return self._models_config
    
    def load_agents_config(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        加载 Agent 配置
        
        Args:
            force_reload: 是否强制重新加载
            
        Returns:
            Agent 配置字典
        """
        if self._agents_config is None or force_reload:
            self._agents_config = self.load_yaml_file(self.agents_config_path)
            self._validate_agents_config()
        
        return self._agents_config
    
    def load_topology_config(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        加载拓扑配置
        
        Args:
            force_reload: 是否强制重新加载
            
        Returns:
            拓扑配置字典
        """
        if self._topology_config is None or force_reload:
            self._topology_config = self.load_yaml_file(self.topology_config_path)
            self._validate_topology_config()
        
        return self._topology_config
    
    def _validate_models_config(self) -> None:
        """
        验证模型配置
        """
        try:
            config = self._models_config
            if not config or "models" not in config:
                raise ConfigurationError("models.yaml 中缺少 'models' 部分")
            
            # 验证每个模型配置
            self._model_specs = []
            for model_config in config["models"]:
                try:
                    model_spec = ModelSpec(**model_config)
                    self._model_specs.append(model_spec)
                except ValidationError as e:
                    raise ConfigurationError(
                        f"模型配置验证失败: {model_config.get('name', 'unknown')}",
                        details={"errors": e.errors()}
                    )
            
            # 验证能力定义
            if "capability_definitions" in config:
                if not isinstance(config["capability_definitions"], dict):
                    raise ConfigurationError("capability_definitions 必须是字典")
            
            # 验证成本层级定义
            if "cost_tier_definitions" in config:
                if not isinstance(config["cost_tier_definitions"], dict):
                    raise ConfigurationError("cost_tier_definitions 必须是字典")
            
            # 验证延迟层级定义
            if "latency_tier_definitions" in config:
                if not isinstance(config["latency_tier_definitions"], dict):
                    raise ConfigurationError("latency_tier_definitions 必须是字典")
            
            logger.info(f"模型配置验证完成，共 {len(self._model_specs)} 个模型")
            
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(
                "模型配置验证失败",
                details={"error": str(e)}
            )
    
    def _validate_agents_config(self) -> None:
        """
        验证 Agent 配置
        """
        try:
            config = self._agents_config
            if not config or "agents" not in config:
                raise ConfigurationError("agents.yaml 中缺少 'agents' 部分")
            
            # 验证每个 Agent 配置
            self._agent_configs = {}
            for agent_name, agent_config in config["agents"].items():
                try:
                    agent_config_dict = agent_config.copy()
                    agent_config_dict["name"] = agent_name
                    agent_cfg = AgentConfig(**agent_config_dict)
                    self._agent_configs[agent_name] = agent_cfg
                except ValidationError as e:
                    raise ConfigurationError(
                        f"Agent 配置验证失败: {agent_name}",
                        details={"errors": e.errors()}
                    )
            
            # 验证 Agent 分组
            if "agent_groups" in config:
                if not isinstance(config["agent_groups"], dict):
                    raise ConfigurationError("agent_groups 必须是字典")
                
                # 验证分组中的 Agent 是否存在
                for group_name, agents in config["agent_groups"].items():
                    for agent_name in agents:
                        if agent_name not in self._agent_configs:
                            raise ConfigurationError(
                                f"Agent 分组 '{group_name}' 中包含不存在的 Agent: {agent_name}"
                            )
            
            logger.info(f"Agent 配置验证完成，共 {len(self._agent_configs)} 个 Agent")
            
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(
                "Agent 配置验证失败",
                details={"error": str(e)}
            )
    
    def _validate_topology_config(self) -> None:
        """
        验证拓扑配置
        """
        try:
            config = self._topology_config
            if not config:
                raise ConfigurationError("topology.yaml 为空")
            
            # 验证默认拓扑
            if "default_topology" not in config:
                raise ConfigurationError("topology.yaml 中缺少 'default_topology'")
            
            # 验证路由规则
            if "routing_rules" in config:
                if not isinstance(config["routing_rules"], dict):
                    raise ConfigurationError("routing_rules 必须是字典")
            
            # 验证拓扑配置
            self._topology_configs = {}
            
            # 验证层级拓扑
            if "hierarchical" in config:
                try:
                    topology_config = config["hierarchical"].copy()
                    topology_config["name"] = "hierarchical"
                    topology_cfg = TopologyConfig(**topology_config)
                    self._topology_configs["hierarchical"] = topology_cfg
                except ValidationError as e:
                    raise ConfigurationError(
                        "层级拓扑配置验证失败",
                        details={"errors": e.errors()}
                    )
            
            # 验证辩论拓扑
            if "debate" in config:
                try:
                    topology_config = config["debate"].copy()
                    topology_config["name"] = "debate"
                    topology_cfg = TopologyConfig(**topology_config)
                    self._topology_configs["debate"] = topology_cfg
                except ValidationError as e:
                    raise ConfigurationError(
                        "辩论拓扑配置验证失败",
                        details={"errors": e.errors()}
                    )
            
            # 验证执行器配置
            if "executor" in config:
                if not isinstance(config["executor"], dict):
                    raise ConfigurationError("executor 必须是字典")
            
            logger.info(f"拓扑配置验证完成，共 {len(self._topology_configs)} 个拓扑")
            
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(
                "拓扑配置验证失败",
                details={"error": str(e)}
            )
    
    def check_for_updates(self) -> bool:
        """
        检查配置文件是否有更新
        
        Returns:
            是否有配置文件被修改
        """
        updated = False
        config_files = [
            (self.models_config_path, "models"),
            (self.agents_config_path, "agents"),
            (self.topology_config_path, "topology"),
        ]
        
        for file_path, config_type in config_files:
            if not file_path.exists():
                continue
            
            current_mtime = file_path.stat().st_mtime
            last_mtime = self._last_modified.get(str(file_path), 0)
            
            if current_mtime > last_mtime:
                logger.info(f"检测到配置文件更新: {config_type}")
                updated = True
        
        return updated
    
    def reload_if_updated(self) -> bool:
        """
        如果配置文件有更新，则重新加载
        
        Returns:
            是否重新加载了配置
        """
        if self.check_for_updates():
            logger.info("配置文件有更新，重新加载...")
            self.load_models_config(force_reload=True)
            self.load_agents_config(force_reload=True)
            self.load_topology_config(force_reload=True)
            return True
        return False
    
    def get_model_specs(self) -> List[ModelSpec]:
        """
        获取所有模型规格
        
        Returns:
            模型规格列表
        """
        if not self._model_specs:
            self.load_models_config()
        return self._model_specs
    
    def get_agent_config(self, agent_name: str) -> Optional[AgentConfig]:
        """
        获取指定 Agent 的配置
        
        Args:
            agent_name: Agent 名称
            
        Returns:
            Agent 配置，如果不存在则返回 None
        """
        if not self._agent_configs:
            self.load_agents_config()
        return self._agent_configs.get(agent_name)
    
    def get_topology_config(self, topology_name: str) -> Optional[TopologyConfig]:
        """
        获取指定拓扑的配置
        
        Args:
            topology_name: 拓扑名称
            
        Returns:
            拓扑配置，如果不存在则返回 None
        """
        if not self._topology_configs:
            self.load_topology_config()
        return self._topology_configs.get(topology_name)
    
    def get_all_agent_configs(self) -> Dict[str, AgentConfig]:
        """
        获取所有 Agent 配置
        
        Returns:
            Agent 名称到配置的映射
        """
        if not self._agent_configs:
            self.load_agents_config()
        return self._agent_configs.copy()
    
    def get_enabled_models(self) -> List[ModelSpec]:
        """
        获取所有启用的模型
        
        Returns:
            启用的模型规格列表
        """
        return [model for model in self.get_model_specs() if model.enabled]
    
    def get_models_by_capability(self, capability: str) -> List[ModelSpec]:
        """
        获取具有指定能力的模型
        
        Args:
            capability: 能力名称
            
        Returns:
            具有该能力的模型规格列表
        """
        return [model for model in self.get_enabled_models() if capability in model.capabilities]
    
    def get_models_by_cost_tier(self, cost_tier: str) -> List[ModelSpec]:
        """
        获取指定成本层级的模型
        
        Args:
            cost_tier: 成本层级
            
        Returns:
            指定成本层级的模型规格列表
        """
        return [model for model in self.get_enabled_models() if model.cost_tier == cost_tier]


# 全局配置管理器实例
config_manager = ConfigManager()