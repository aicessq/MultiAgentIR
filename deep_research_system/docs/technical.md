# Deep Research System - 技术文档

## 1. 技术栈

### 1.1 核心框架

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 后端框架 | FastAPI | 0.100+ | REST API 和 SSE 流式传输 |
| 图编排 | LangGraph | 0.1.0+ | 多智能体工作流编排 |
| 类型提示 | Python TypedDict | - | 状态类型定义 |
| 数据验证 | Pydantic | 2.0+ | 请求/响应验证 |
| 异步支持 | asyncio | - | 异步执行和并发 |

### 1.2 基础设施

| 组件 | 技术 | 用途 |
|------|------|------|
| 检查点存储 | PostgreSQL | 图状态持久化 |
| 事件队列 | Redis Streams | 事件日志和消息传递 |
| 分布式锁 | Redis | 并发控制 |
| 缓存 | Redis | 结果缓存 |

### 1.3 前端

| 组件 | 技术 | 用途 |
|------|------|------|
| 框架 | Vue 3 | 前端框架 |
| 状态管理 | Pinia | 全局状态管理 |
| UI 组件 | Element Plus | UI 组件库 |
| 数据流 | SSE (EventSource) | 实时事件订阅 |

## 2. 项目结构

```
deep_research_system/
├── app/                              # 应用核心代码
│   ├── __init__.py
│   ├── agents/                       # 智能体实现
│   │   ├── __init__.py
│   │   ├── base.py                   # 智能体基类
│   │   ├── analyzer.py               # 分析智能体
│   │   ├── critic.py                 # 批判智能体
│   │   ├── debate.py                 # 辩论智能体
│   │   ├── planner.py                # 规划智能体
│   │   ├── reader.py                 # 文档读取智能体
│   │   ├── searcher.py               # 搜索智能体
│   │   ├── validator.py              # 验证智能体
│   │   └── writer.py                 # 写作智能体
│   ├── api/                          # REST API
│   │   ├── __init__.py
│   │   ├── routes.py                 # 路由注册
│   │   ├── routes_health.py          # 健康检查
│   │   ├── routes_models.py          # 模型管理
│   │   └── routes_research.py        # 研究任务 API
│   ├── config/                       # 配置管理
│   │   ├── __init__.py
│   │   └── effective_config.py       # 有效配置
│   ├── core/                         # 核心模块
│   │   ├── __init__.py
│   │   ├── config.py                 # 配置加载
│   │   ├── errors.py                 # 自定义异常
│   │   ├── logging.py                # 日志配置
│   │   ├── security.py               # 安全工具
│   │   └── middleware.py             # 中间件
│   ├── domain/                       # 领域模型
│   │   ├── __init__.py
│   │   ├── enums.py                  # 枚举定义
│   │   └── errors.py                 # 领域异常
│   ├── frontend/                     # 前端集成
│   │   ├── __init__.py
│   │   ├── progress.py               # 进度追踪
│   │   └── streaming.py              # SSE 格式化
│   ├── gateways/                     # 外部服务网关
│   │   ├── fetch/                    # 文档获取
│   │   ├── model/                    # 模型调用
│   │   ├── search/                   # 搜索服务
│   │   └── storage/                  # 存储服务
│   ├── graphs/                       # LangGraph 定义
│   │   ├── debate/                   # 辩论图
│   │   │   ├── __init__.py
│   │   │   ├── builder.py            # 图构建器
│   │   │   ├── nodes.py              # 节点实现
│   │   │   └── state.py              # 状态定义
│   │   ├── hierarchical/             # 层级图
│   │   │   ├── __init__.py
│   │   │   ├── builder.py
│   │   │   ├── nodes.py
│   │   │   └── state.py
│   │   ├── research_branch/          # 研究分支子图
│   │   ├── root/                     # 根状态
│   │   └── shared/                   # 共享组件
│   │       └── reducers.py           # 状态合并器
│   ├── infrastructure/               # 基础设施
│   │   ├── checkpoint/               # 检查点存储
│   │   │   └── postgres.py
│   │   ├── db/                       # 数据库
│   │   ├── events/                   # 事件发布
│   │   │   └── publisher.py
│   │   └── redis/                    # Redis 工具
│   │       └── streams.py
│   ├── model_pool/                   # 模型池
│   │   ├── __init__.py
│   │   ├── circuit_breaker.py        # 熔断机制
│   │   ├── client.py                 # 模型客户端
│   │   ├── key_pool.py               # API Key 池
│   │   ├── registry.py               # 模型注册
│   │   └── router.py                 # 模型路由
│   ├── prompts/                      # 提示词管理
│   │   ├── __init__.py
│   │   ├── loader.py                 # 加载器
│   │   └── renderer.py               # 渲染器
│   ├── schemas/                      # API Schema
│   │   ├── __init__.py
│   │   ├── agent_outputs.py          # 智能体输出
│   │   ├── model.py                  # 模型定义
│   │   ├── response.py               # 响应格式
│   │   ├── state.py                  # 状态 Schema
│   │   └── task.py                   # 任务定义
│   ├── services/                     # 业务服务
│   │   ├── __init__.py
│   │   ├── cache_service.py          # 缓存服务
│   │   ├── config_service.py         # 配置服务
│   │   ├── research_service.py       # 研究服务
│   │   ├── search_service.py         # 搜索服务
│   │   ├── task_state_store.py       # 任务状态存储
│   │   └── trace_service.py          # 追踪服务
│   ├── topology/                     # 拓扑管理
│   │   ├── __init__.py
│   │   ├── base.py                   # 拓扑基类
│   │   ├── debate.py                 # 辩论拓扑
│   │   ├── hierarchical.py           # 层级拓扑
│   │   └── router.py                 # 拓扑路由
│   ├── utils/                        # 工具函数
│   │   ├── __init__.py
│   │   ├── ids.py                    # ID 生成
│   │   └── time.py                   # 时间工具
│   ├── validators/                   # 验证器
│   │   ├── __init__.py
│   │   └── report_validator.py       # 报告验证
│   └── worker/                       # 工作进程
│       └── process.py
├── config/                           # 配置文件
│   ├── agents.yaml                  # 智能体配置
│   ├── app.yaml                     # 应用配置
│   ├── models.yaml                  # 模型配置
│   └── topology.yaml                # 拓扑配置
├── docs/                            # 文档
│   ├── migration/                   # 迁移文档
│   ├── architecture.md              # 架构文档
│   └── technical.md                 # 技术文档
├── frontend/                        # 前端代码
│   ├── src/
│   ├── dist/
│   └── index.html
├── tests/                           # 测试用例
├── .env.example                     # 环境变量示例
└── main.py                          # 启动入口
```

## 3. 核心模块详解

### 3.1 图状态管理

#### 3.1.1 状态定义模式

系统使用 TypedDict + Annotated Reducers 模式：

```python
from typing import Annotated, TypedDict
from app.graphs.shared.reducers import merge_unique_strings, merge_dict, override

class DebateState(TypedDict, total=False):
    hypotheses: Annotated[list[str], merge_unique_strings]
    debate_positions: Annotated[dict[str, str], merge_dict]
    status: Annotated[str, override]
```

**设计优势**：
- **类型安全**：利用 Python 类型系统进行编译时检查
- **自动合并**：Reducer 自动处理状态合并逻辑
- **无副作用**：Reducer 是纯函数，保证状态变化可预测
- **支持并发**：合并策略支持并行执行场景

#### 3.1.2 Reducer 实现

```python
def merge_unique_strings(existing: list[str], updates: list[str]) -> list[str]:
    """去重合并列表，保持顺序"""
    result = list(existing)
    for item in updates:
        if item not in result:
            result.append(item)
    return result

def merge_dict(existing: dict, updates: dict) -> dict:
    """字典合并，更新值优先"""
    return {**existing, **updates}

def override(existing, updates):
    """直接覆盖"""
    return updates
```

### 3.2 图节点实现

#### 3.2.1 节点函数签名

所有节点遵循统一的签名模式：

```python
async def node_function(state: StateType) -> dict:
    """节点逻辑实现"""
    # 1. 从 state 中读取输入
    input_data = state.get("input_key")
    
    # 2. 执行业务逻辑
    result = await execute_business_logic(input_data)
    
    # 3. 返回状态更新
    return {
        "output_key": result,
        "status": "completed",
    }
```

#### 3.2.2 路由节点

路由节点返回下一个节点名称：

```python
def validation_router(state: DebateState) -> str:
    decision = state.get("validation_decision")
    repair_count = state.get("repair_count", 0)
    
    if decision == QualityDecision.PASS.value:
        return "finalize_debate"
    elif decision == QualityDecision.REPAIR.value and repair_count < MAX_REPAIRS:
        return "repair_report"
    else:
        return "quality_gate_failed"
```

### 3.3 图构建器

#### 3.3.1 DebateGraphBuilder

```python
class DebateGraphBuilder:
    def __init__(self, model_gateway, search_gateway, document_fetcher, artifact_store):
        self._model_gateway = model_gateway
        self._search_gateway = search_gateway
        self._document_fetcher = document_fetcher
        self._artifact_store = artifact_store
    
    def build(self) -> dict:
        return {
            "type": "debate",
            "nodes": {
                "generate_hypotheses": {
                    "func": generate_hypotheses_node,
                    "next": "dispatch_debate_branches",
                },
                # ... 其他节点
            },
            "entry": "generate_hypotheses",
        }
    
    async def run(self, initial_state: DebateState) -> DebateState:
        # 执行图逻辑
        graph = self.build()
        state = dict(initial_state)
        current = graph["entry"]
        
        while current and not is_terminal(state):
            node = graph["nodes"][current]
            update = await node["func"](state)
            state = merge_state(state, update)
            current = node.get("next")
        
        return state
```

### 3.4 事件系统

#### 3.4.1 事件类型定义

```python
class EventType(str, Enum):
    # 运行生命周期
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    
    # 节点事件
    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"
    
    # 质量门
    QUALITY_GATE_PASSED = "quality_gate_passed"
    QUALITY_GATE_FAILED = "quality_gate_failed"
```

#### 3.4.2 事件发布

```python
class EventPublisher:
    def __init__(self, event_logger):
        self._event_logger = event_logger
        self._sequence: dict[str, int] = {}
    
    async def publish(self, run_id, thread_id, event_type, **kwargs):
        self._sequence[run_id] += 1
        event = ResearchEvent(
            event_id=str(uuid.uuid4()),
            sequence=self._sequence[run_id],
            run_id=run_id,
            thread_id=thread_id,
            type=event_type,
            **kwargs
        )
        await self._event_logger.publish(event)
```

### 3.5 SSE 流式传输

#### 3.5.1 SSE 格式化

```python
class SSEFormatter:
    @staticmethod
    def format_event(event: ResearchEvent) -> str:
        sse_data = event.to_sse()
        lines = [
            f"event: {sse_data['event']}",
            f"id: {sse_data['id']}",
            f"data: {sse_data['data']}",
            "",
        ]
        return "\n".join(lines)
    
    @staticmethod
    def format_progress(progress: int, stage: str, run_id: str) -> str:
        data = json.dumps({
            "type": "progress",
            "progress": progress,
            "stage": stage,
            "run_id": run_id,
        }, ensure_ascii=False)
        return f"event: progress\nid: 0\ndata: {data}\n\n"
```

#### 3.5.2 事件流消费者

```python
class EventStreamConsumer:
    def __init__(self, event_publisher, run_id, keepalive_interval=30.0):
        self._publisher = event_publisher
        self._run_id = run_id
        self._keepalive_interval = keepalive_interval
    
    async def stream(self) -> AsyncIterator[str]:
        # 重放历史事件
        async for event in self._publisher.replay(self._run_id):
            yield SSEFormatter.format_event(event)
        
        # 实时流 + keepalive
        while True:
            try:
                await asyncio.wait_for(
                    self._wait_for_next_event(),
                    timeout=self._keepalive_interval
                )
            except asyncio.TimeoutError:
                yield SSEFormatter.keepalive()
```

## 4. API 接口

### 4.1 研究任务

#### 4.1.1 创建研究任务

**POST** `/api/research`

请求体：
```json
{
    "query": "分析人工智能行业发展趋势",
    "task_type": "industry_analysis",
    "max_repairs": 2,
    "writer_template": "writer/industry_report.zh.j2"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | 是 | 用户查询 |
| `task_type` | string | 是 | 任务类型 |
| `max_repairs` | int | 否 | 最大修复次数，默认 2 |
| `writer_template` | string | 否 | 写作模板 |

响应：
```json
{
    "code": 0,
    "message": "success",
    "data": {
        "task_id": "task-abc123",
        "status": "running",
        "progress": 0,
        "current_stage": "init",
        "selected_topology": "hierarchical",
        "created_at": "2024-01-01T00:00:00Z"
    }
}
```

#### 4.1.2 获取任务状态

**GET** `/api/research/{task_id}`

响应：
```json
{
    "code": 0,
    "message": "success",
    "data": {
        "task_id": "task-abc123",
        "status": "completed",
        "progress": 100,
        "current_stage": "completed",
        "selected_topology": "hierarchical",
        "created_at": "2024-01-01T00:00:00Z",
        "result": {
            "report": {...},
            "claim_graph": [...],
            "metrics": {...}
        }
    }
}
```

#### 4.1.3 SSE 事件流

**GET** `/api/research/{task_id}/stream`

响应格式（SSE）：
```
event: start
id: 0
data: {"type": "start", "topology": "hierarchical", "progress": 0}

event: progress
id: 0
data: {"type": "progress", "progress": 10, "stage": "search", "run_id": "task-abc123"}

event: done
id: 0
data: {"type": "done", "run_id": "task-abc123", "result": {...}}
```

#### 4.1.4 取消任务

**POST** `/api/research/{task_id}/cancel`

响应：
```json
{
    "code": 0,
    "message": "success",
    "data": {
        "task_id": "task-abc123",
        "status": "cancelled"
    }
}
```

### 4.2 健康检查

**GET** `/api/health`

响应：
```json
{
    "code": 0,
    "message": "success",
    "data": {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z"
    }
}
```

## 5. 数据流示例

### 5.1 层级式研究执行流程

```python
# 1. 创建任务
task = await research_service.create_task({
    "user_query": "分析新能源汽车市场",
    "task_type": "industry_analysis"
})

# 2. 执行流程
state = await hierarchical_topology.execute(initial_state)

# 状态流转：
# prepare_research → dispatch_research_wave → research_branch × N 
# → join_research → build_analysis → critique → write_report 
# → validate_report → finalize_hierarchical

# 3. 事件发布
await event_publisher.publish_node_started(run_id, thread_id, "search")
await event_publisher.publish_node_completed(run_id, thread_id, "search", {"evidence_count": 10})
```

### 5.2 辩论式研究执行流程

```python
# 1. 生成假设
hypotheses = [
    "Hypothesis A: 新能源汽车市场将持续增长",
    "Hypothesis B: 新能源汽车市场面临瓶颈",
    "Hypothesis C: 新能源汽车市场需要政策支持"
]

# 2. 分发辩论分支
branches = {
    "support-0": {"hypothesis": hypotheses[0], "position": "support"},
    "oppose-0": {"hypothesis": hypotheses[0], "position": "oppose"},
    "alternative-0": {"hypothesis": hypotheses[0], "position": "alternative"},
    # ...
}

# 3. 交叉检验
findings = [
    {
        "type": "conflict",
        "description": "Support and oppose have conflicting evidence",
        "support_count": 5,
        "oppose_count": 3
    }
]

# 4. 综合
claim_graph = [
    {"branch_id": "support-0", "position": "support", "evidence_count": 5},
    {"branch_id": "oppose-0", "position": "oppose", "evidence_count": 3},
]
```

## 6. 配置管理

### 6.1 配置文件结构

**config/topology.yaml**：
```yaml
default_topology: hierarchical
routing_rules:
  industry_analysis:
    topology: hierarchical
    writer_template: writer/industry_report.zh.j2
  strategy_decision:
    topology: debate
    writer_template: writer/strategy_report.zh.j2
  default:
    topology: hierarchical
    writer_template: writer/default.zh.j2
```

**config/app.yaml**：
```yaml
debug: false
log_level: INFO
max_concurrent_tasks: 10
max_repair_attempts: 2
```

### 6.2 环境变量

```bash
# 数据库配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=research
POSTGRES_USER=admin
POSTGRES_PASSWORD=password

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# 模型配置
OPENAI_API_KEY=your-api-key
MAX_TOKENS=4096
```

## 7. 测试策略

### 7.1 测试结构

```
tests/
├── test_phase1_domain.py          # 领域模型测试
├── test_phase2_research_branch.py # 研究分支测试
├── test_phase3_hierarchical.py    # 层级图测试
├── test_phase4_checkpoint.py      # 检查点测试
├── test_phase5_debate.py          # 辩论图测试
└── test_phase6_frontend.py        # 前端集成测试
```

### 7.2 测试覆盖

| 测试类型 | 覆盖内容 | 测试数量 |
|----------|----------|----------|
| 领域模型 | 枚举、状态定义 | 10+ |
| 图节点 | 各节点业务逻辑 | 30+ |
| 状态管理 | Reducer 合并逻辑 | 15+ |
| 质量门 | 验证和修复流程 | 10+ |
| 事件系统 | 事件发布和消费 | 10+ |
| SSE 格式化 | 事件转 SSE 格式 | 10+ |
| 进度追踪 | 拓扑进度映射 | 10+ |

### 7.3 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定阶段测试
python -m pytest tests/test_phase5_debate.py -v

# 生成覆盖率报告
python -m pytest tests/ --cov=app/ --cov-report=html
```

## 8. 部署指南

### 8.1 依赖安装

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r requirements-dev.txt
```

### 8.2 启动服务

```bash
# 开发模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 8.3 Docker 部署

**Dockerfile**：
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml**：
```yaml
version: "3.8"
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=research
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## 9. 扩展开发

### 9.1 新增研究策略

1. **创建状态类**：
```python
class CustomState(TypedDict, total=False):
    custom_field: Annotated[list[str], merge_unique_strings]
    # ... 其他字段
```

2. **实现节点**：
```python
async def custom_node(state: CustomState) -> dict:
    # 业务逻辑
    return {"custom_field": ["value"]}
```

3. **创建图构建器**：
```python
class CustomGraphBuilder:
    def build(self) -> dict:
        return {
            "type": "custom",
            "nodes": {...},
            "entry": "start_node",
        }
```

4. **注册路由**：
```python
# config/topology.yaml
routing_rules:
  custom_task_type:
    topology: custom
```

### 9.2 新增智能体

```python
class CustomAgent(BaseAgent):
    def __init__(self, model_gateway):
        super().__init__(model_gateway)
        self._prompt_template = "custom_prompt.j2"
    
    async def execute(self, input_data: dict) -> dict:
        prompt = self._render_prompt(input_data)
        response = await self._model_gateway.complete(prompt)
        return self._parse_response(response)
```

## 10. 故障排除

### 10.1 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 任务无法启动 | Redis 连接失败 | 检查 Redis 配置和网络 |
| 检查点保存失败 | PostgreSQL 连接失败 | 检查数据库配置 |
| 模型调用超时 | API Key 无效或限流 | 检查密钥和配额 |
| SSE 连接断开 | 超时无数据 | 检查 keepalive 配置 |
| 质量门失败 | 报告验证不通过 | 调整验证阈值或修复逻辑 |

### 10.2 日志排查

```bash
# 查看最近的错误日志
grep -E "ERROR|exception" app.log | tail -20

# 查看特定任务的日志
grep "task-abc123" app.log

# 查看节点执行时间
grep "node_completed" app.log | jq '.duration_ms'
```