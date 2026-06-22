# Deep Research System - 架构文档

## 1. 系统概述

Deep Research System 是一个基于 LangGraph 的多智能体研究系统，支持两种研究策略拓扑：**层级式研究**（Hierarchical）和**辩论式研究**（Debate）。系统通过 SSE 流式传输实现实时进度追踪，并提供报告验证和质量门机制确保输出质量。

### 1.1 核心价值

| 特性 | 描述 |
|------|------|
| **多策略支持** | 层级式研究用于行业报告分析，辩论式研究用于开放式问题决策 |
| **实时流式输出** | 通过 SSE 实现实时进度更新和报告预览 |
| **质量保障** | 报告验证和自动修复机制，确保输出质量 |
| **可扩展性** | 基于 LangGraph 的图架构，易于扩展新节点和策略 |
| **持久化支持** | PostgreSQL 检查点和 Redis Streams 事件日志 |

## 2. 架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        前端层 (Vue 3 + Pinia)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │ResearchView │  │ProgressBar │  │DetailPanel  │  │ ReportViewer│   │
│  └──────┬──────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
│         │ SSE Streaming                                                │
└─────────┼───────────────────────────────────────────────────────────────┘
          │
┌─────────┼───────────────────────────────────────────────────────────────┐
│                        API 层 (FastAPI)                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  /api/research          POST 创建研究任务                        │   │
│  │  /api/research/{id}     GET 获取任务状态                        │   │
│  │  /api/research/{id}/stream GET SSE 事件流                       │   │
│  │  /api/research/{id}/cancel POST 取消任务                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────┼───────────────────────────────────────────────────────────────┘
          │
┌─────────┼───────────────────────────────────────────────────────────────┐
│                      服务层 (ResearchService)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │TopologyRouter│  │  TraceService│  │CacheService│  │ TaskManager │   │
│  └──────┬──────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
│         │ 路由策略选择                                                  │
└─────────┼───────────────────────────────────────────────────────────────┘
          │
┌─────────┼───────────────────────────────────────────────────────────────┐
│                    拓扑层 (Topology Layer)                             │
│  ┌─────────────────────────┐  ┌─────────────────────────┐            │
│  │   HierarchicalTopology  │  │    DebateTopology       │            │
│  │   ┌─────────────────┐   │  │   ┌─────────────────┐   │            │
│  │   │HierarchicalGraph│   │  │   │  DebateGraph    │   │            │
│  │   │ Builder         │   │  │   │   Builder       │   │            │
│  │   └─────────────────┘   │  │   └─────────────────┘   │            │
│  │                         │  │                         │            │
│  │  prepare -> dispatch -> │  │  generate -> dispatch ->│            │
│  │  [branches] -> join ->  │  │  [debate_branches] ->   │            │
│  │  analyze -> critique -> │  │  join -> cross_examine ->│            │
│  │  write -> validate ->   │  │  synthesize -> write ->  │            │
│  │  [finalize/repair]      │  │  validate -> [finalize/repair]        │
│  └─────────────────────────┘  └─────────────────────────┘            │
└─────────┼───────────────────────────────────────────────────────────────┘
          │
┌─────────┼───────────────────────────────────────────────────────────────┐
│                      图层 (LangGraph)                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │  State      │  │  Nodes      │  │  Reducers   │  │ Checkpoints │   │
│  │  TypedDict  │  │  (业务逻辑) │  │  (状态合并) │  │  (持久化)   │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────┼───────────────────────────────────────────────────────────────┘
          │
┌─────────┼───────────────────────────────────────────────────────────────┐
│                      基础设施层                                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │  ModelPool  │  │  SearchAPI  │  │  Redis      │  │PostgreSQL  │   │
│  │  (LLM路由)  │  │  (搜索网关) │  │(事件流/锁)  │  │(检查点存储) │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 模块职责

| 模块 | 职责 | 核心文件 |
|------|------|----------|
| **API 层** | REST API 暴露，SSE 流式传输 | `app/api/routes_research.py` |
| **服务层** | 任务管理、缓存、跟踪 | `app/services/research_service.py` |
| **拓扑层** | 研究策略路由和执行 | `app/topology/` |
| **图层** | LangGraph 状态和节点定义 | `app/graphs/` |
| **基础设施** | 外部服务网关和持久化 | `app/infrastructure/`, `app/gateways/` |
| **前端集成** | SSE 格式化和进度追踪 | `app/frontend/` |

## 3. 核心组件

### 3.1 状态管理

系统使用 TypedDict + Annotated Reducers 模式管理图状态：

```python
class DebateState(TypedDict, total=False):
    # 假设生成
    hypotheses: Annotated[list[str], merge_unique_strings]
    current_hypothesis_index: int
    
    # 辩论分支
    debate_positions: Annotated[dict[str, str], merge_dict]
    debate_results: Annotated[dict[str, dict], merge_dict]
    
    # 综合与报告
    synthesis_id: Annotated[str | None, override]
    report_revision_id: Annotated[str | None, override]
    
    # 验证与修复
    validation_decision: str | None
    repair_count: Annotated[int, max_int]
```

**Reducer 类型**：

| Reducer | 用途 | 示例字段 |
|---------|------|----------|
| `merge_unique_strings` | 去重合并列表 | `evidence_ids`, `hypotheses` |
| `merge_dict` | 字典合并 | `debate_positions`, `debate_results` |
| `append_list` | 追加列表 | `errors`, `warnings`, `repair_instructions` |
| `max_int` | 取最大值 | `repair_count`, `research_round` |
| `override` | 直接覆盖 | `status`, `synthesis_id`, `report_revision_id` |

### 3.2 图节点设计

#### 3.2.1 层级式研究图节点

| 节点 | 职责 | 输入 | 输出 |
|------|------|------|------|
| `prepare_research` | 初始化研究任务 | query, task_type | research_plan |
| `dispatch_research_wave` | 分发研究子任务 | research_plan | pending_subtasks |
| `research_branch` | 执行单个研究分支 | subtask | evidence, findings |
| `join_research` | 汇总分支结果 | branch_results | merged_evidence |
| `build_analysis` | 构建分析报告 | evidence | analysis_revision_id |
| `critique` | 批判性审查 | analysis | critique_findings |
| `critique_router` | 根据审查结果路由 | critique_decision | next_node |
| `generate_followups` | 生成后续研究问题 | gaps | followup_queries |
| `write_report` | 撰写最终报告 | analysis, evidence | report_revision_id |
| `validate_report` | 验证报告质量 | report | validation_result |
| `validation_router` | 根据验证结果路由 | validation_decision | next_node |
| `repair_report` | 修复报告问题 | repair_instructions | updated_report |
| `finalize_hierarchical` | 完成任务 | - | terminal_state |
| `quality_gate_failed` | 质量门失败 | - | terminal_state |

#### 3.2.2 辩论式研究图节点

| 节点 | 职责 | 输入 | 输出 |
|------|------|------|------|
| `generate_hypotheses` | 生成假设 | query | hypotheses |
| `dispatch_debate_branches` | 分发辩论分支 | hypotheses | debate_positions |
| `debate_branch` | 执行辩论分支 | hypothesis, position | evidence |
| `join_debate` | 汇总辩论结果 | branch_results | merged_evidence |
| `cross_examine` | 交叉检验立场冲突 | debate_results | findings |
| `synthesize` | 综合辩论观点 | findings | claim_graph, synthesis_id |
| `write_report` | 撰写报告 | synthesis | report_revision_id |
| `validate_report` | 验证报告质量 | report | validation_result |
| `validation_router` | 根据验证结果路由 | validation_decision | next_node |
| `repair_report` | 修复报告 | repair_instructions | updated_report |
| `finalize_debate` | 完成任务 | - | terminal_state |
| `quality_gate_failed` | 质量门失败 | - | terminal_state |

### 3.3 拓扑路由器

`TopologyRouter` 根据任务类型选择合适的研究策略：

```python
class TopologyRouter:
    def route(self, task_type: str) -> tuple[str, str]:
        # 示例路由规则
        # industry_analysis -> hierarchical
        # strategy_decision -> debate
        # default -> hierarchical
```

### 3.4 事件发布系统

`EventPublisher` 将图执行事件发布到 Redis Streams：

```python
class ResearchEvent(BaseModel):
    event_id: str
    sequence: int
    run_id: str
    thread_id: str
    type: EventType  # RUN_STARTED, NODE_STARTED, NODE_COMPLETED, etc.
    node: str | None
    payload: dict
```

**事件类型**：

| 事件类型 | 触发时机 |
|----------|----------|
| `RUN_STARTED` | 研究任务开始 |
| `RUN_COMPLETED` | 研究任务完成 |
| `RUN_FAILED` | 研究任务失败 |
| `NODE_STARTED` | 节点开始执行 |
| `NODE_COMPLETED` | 节点执行完成 |
| `QUALITY_GATE_PASSED` | 质量门通过 |
| `QUALITY_GATE_FAILED` | 质量门失败 |

### 3.5 SSE 流式传输

`SSEFormatter` 将事件格式化为 SSE 格式供前端消费：

```python
class SSEFormatter:
    @staticmethod
    def format_event(event: ResearchEvent) -> str:
        # event: node_completed
        # id: 123
        # data: {...}
```

`ResearchRunStreamer` 提供事件重放和实时流：

```python
class ResearchRunStreamer:
    async def stream_run(self, run_id: str, after_sequence: int = 0):
        # 1. 重放历史事件
        # 2. 流传输实时事件
        # 3. 发送 keepalive ping
```

## 4. 数据流

### 4.1 请求处理流程

```
客户端请求 → API层 → ResearchService → TopologyRouter → Graph执行 → 事件发布 → SSE推送
```

### 4.2 层级式研究数据流

```
prepare_research → dispatch_research_wave → [research_branch × N] → join_research
    → build_analysis → critique → critique_router
        ├─→ write_report → validate_report → validation_router
        │       ├─→ finalize_hierarchical (PASS)
        │       └─→ repair_report → write_report (REPAIR)
        └─→ generate_followups → dispatch_research_wave (需要补充研究)
```

### 4.3 辩论式研究数据流

```
generate_hypotheses → dispatch_debate_branches → [debate_branch × N] → join_debate
    → cross_examine → synthesize → write_report → validate_report → validation_router
        ├─→ finalize_debate (PASS)
        └─→ repair_report → write_report (REPAIR)
```

## 5. 质量保障机制

### 5.1 报告验证流程

```
write_report → validate_report → validation_router
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
         PASS (≥85)              REPAIR (<85)           FAILED (max_repairs)
              │                       │                       │
              ▼                       ▼                       ▼
    finalize_hierarchical     repair_report →           quality_gate_failed
                            write_report (循环)
```

### 5.2 验证决策枚举

```python
class QualityDecision(str, Enum):
    PASS = "pass"      # 直接通过
    REPAIR = "repair"  # 需要修复
    FAIL = "fail"      # 直接失败
```

### 5.3 辩论立场枚举

```python
class DebatePosition(str, Enum):
    SUPPORT = "support"       # 支持假设
    OPPOSE = "oppose"         # 反对假设
    ALTERNATIVE = "alternative" # 替代观点
```

## 6. 持久化设计

### 6.1 检查点存储

使用 PostgreSQL 存储图执行检查点：

```python
class AsyncPostgresSaver(BaseCheckpointSaver):
    async def aput(self, checkpoint_id: str, checkpoint: Checkpoint):
        # 存储检查点到 PostgreSQL
```

### 6.2 事件日志

使用 Redis Streams 存储事件日志：

```python
class EventLogger:
    async def publish(self, run_id: str, thread_id: str, event_type: str, **kwargs):
        # 发布事件到 Redis Stream
```

## 7. 安全考虑

### 7.1 SSRF 保护

文档获取器实现 URL 验证：

| 规则 | 说明 |
|------|------|
| 允许的协议 | http://, https:// |
| 允许的域名 | 配置白名单 |
| 禁止的 IP | 10.x, 172.16.x, 192.168.x (内网) |

### 7.2 输入验证

- 使用 Pydantic 模型验证请求参数
- 限制请求大小和频率
- 对用户输入进行清理和转义

### 7.3 敏感信息保护

- 不在日志中记录敏感数据
- API 密钥使用环境变量管理
- 响应中不暴露内部系统信息

## 8. 扩展性设计

### 8.1 新增研究策略

1. 创建新的状态类（继承或扩展现有状态）
2. 实现图节点逻辑
3. 创建图构建器
4. 在 TopologyRouter 中注册路由规则

### 8.2 新增节点类型

1. 实现节点函数（接收状态，返回状态更新）
2. 在图构建器中注册节点
3. 添加路由逻辑（如需要）

### 8.3 新增事件类型

1. 在 `EventType` 枚举中添加新类型
2. 更新 `SSEFormatter` 支持新事件
3. 更新前端事件处理器

## 9. 部署架构

### 9.1 组件部署

| 组件 | 推荐部署方式 | 说明 |
|------|-------------|------|
| API 服务 | Docker/K8s | 无状态服务，可水平扩展 |
| Redis | Redis Cluster | 事件流和分布式锁 |
| PostgreSQL | PostgreSQL 主从 | 检查点存储 |
| LLM 网关 | 内部服务 | 模型路由和限流 |

### 9.2 网络架构

```
┌─────────────────────────────────────────────────────┐
│              Load Balancer                          │
│    (Nginx / Cloud Load Balancer)                   │
└───────────────────┬─────────────────────────────────┘
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
┌───────┐      ┌───────┐      ┌───────┐
│ API 1 │      │ API 2 │      │ API N │
└───────┘      └───────┘      └───────┘
    │               │               │
    └───────────────┼───────────────┘
                    │
    ┌───────────────┴───────────────┐
    ▼                               ▼
┌─────────┐                   ┌───────────┐
│  Redis  │                   │ PostgreSQL│
└─────────┘                   └───────────┘
```

## 10. 监控与可观测性

### 10.1 日志

- **结构化日志**：JSON 格式，包含 request_id, run_id, timestamp
- **日志级别**：DEBUG, INFO, WARNING, ERROR
- **输出目标**：控制台、文件、ELK Stack

### 10.2 指标

| 指标 | 说明 |
|------|------|
| `run_duration_ms` | 研究任务耗时 |
| `token_usage` | 令牌消耗 |
| `node_execution_count` | 节点执行次数 |
| `quality_gate_pass_rate` | 质量门通过率 |
| `repair_count` | 报告修复次数 |

### 10.3 追踪

使用 TraceService 记录任务执行轨迹：

```python
class TraceService:
    def record(self, task_id: str, state: ResearchState):
        # 记录任务执行轨迹
```