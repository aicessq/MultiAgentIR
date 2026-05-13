# 异构模型协同 Deep Research 系统开发文档

**项目定位**：在成本约束下，通过异构模型路由、Agent 角色拆分与可切换拓扑编排，自动完成高质量深度研究报告生成。

**核心命题**：不是简单的“多 Agent 检索系统”，而是一个“异构模型协同的 Deep Research 框架”。系统根据任务类型、模型能力、成本、延迟与上下文需求，自动选择合适模型与拓扑结构，用便宜模型铺量，用强模型把关，用可插拔拓扑适配不同研究场景。

---

## 1. 项目目标

### 1.1 核心目标

构建一个可扩展的 Deep Research 系统，支持用户输入一个研究主题后，系统自动完成：

1. 研究任务理解与拆解；
2. 子问题规划；
3. 多轮网页/知识库检索；
4. 信息阅读、摘要与引用抽取；
5. 跨信源分析与矛盾识别；
6. 批判性审稿与事实校验；
7. 结构化研究报告生成；
8. 全链路成本、延迟、Token 与模型使用记录。

### 1.2 项目亮点

- **异构模型协同**：不同 Agent 根据能力需求自动路由到不同模型。
- **成本-质量权衡**：低成本模型负责搜索、阅读、初步分析，高能力模型负责规划、审稿与最终写作。
- **双拓扑编排**：行业报告走层级式拓扑，开放性问题走辩论式拓扑。
- **配置驱动扩展**：新增模型、Agent、Prompt、拓扑、评测指标时尽量不改核心代码。
- **工程化可观测性**：记录模型调用、成本、延迟、Prompt 版本、Agent 行为与审计日志。
- **安全扩展预留**：预留 Prompt Injection 检测、PII 脱敏、审计追踪、引用校验等接口。

---

## 2. 总体架构

系统采用三层解耦架构：

```text
┌─────────────────────────────────────────────┐
│  Layer 3: 拓扑编排层 Topology Layer          │
│  - Hierarchical / Debate / Pipeline          │
│  - 每种拓扑是一个可插拔 Strategy             │
├─────────────────────────────────────────────┤
│  Layer 2: Agent 角色层 Agent Layer           │
│  - Planner / Searcher / Reader / Analyzer    │
│  - Critic / Writer / Validator               │
│  - 每个 Agent 只声明能力需求，不绑定模型      │
├─────────────────────────────────────────────┤
│  Layer 1: 模型能力池 Model Pool Layer        │
│  - 模型注册表 + 能力标签 + Key 池             │
│  - 成本 / 能力 / 延迟 / 负载路由              │
└─────────────────────────────────────────────┘
```

### 2.1 分层原则

| 层级 | 责任 | 可扩展点 |
|---|---|---|
| Model Pool Layer | 管理模型、API Key、熔断、路由 | 新模型、新供应商、新路由策略 |
| Agent Layer | 定义研究角色、Prompt 模板、输入输出 Schema | 新 Agent、新 Prompt、新角色能力需求 |
| Topology Layer | 编排 Agent 执行顺序、并行关系与循环逻辑 | 新拓扑、新任务路由规则 |

### 2.2 关键设计原则

1. **Agent 不直接调用具体模型**：Agent 只声明 `TaskRequirement`，由 Router 选择模型。
2. **拓扑不关心模型细节**：拓扑只编排 Agent，不绑定具体供应商。
3. **Prompt 不硬编码**：Prompt 通过模板文件加载，并支持版本管理。
4. **状态隔离**：每个子问题有独立 namespace，避免一个子任务污染全局研究状态。
5. **所有调用可追踪**：每次 LLM 调用都记录模型名、Agent、Prompt 版本、耗时、Token、成本和错误信息。

---

## 3. 技术选型

### 3.1 后端技术栈

| 技术 | 用途 |
|---|---|
| Python 3.11+ | 主开发语言 |
| FastAPI | API 服务与 OpenAPI 文档 |
| Pydantic v2 | Schema 校验与配置建模 |
| httpx | 异步 HTTP 调用模型 API 和搜索 API |
| asyncio | 并发执行 Searcher / Reader / Debate 分支 |
| LangGraph | 简单流程图和状态机编排 |
| Redis | 任务状态、缓存、限流、Key 状态、调用日志 |
| tenacity | 重试、退避、错误恢复 |
| ruff / mypy / pytest | 工程质量保障 |

### 3.2 编排方案

采用 **LangGraph + asyncio 混合编排**：

- 简单主流程、条件边、状态流转使用 LangGraph；
- 多 Searcher 并发、多 Reader 并发、Debate 多模型并行使用 asyncio；
- 这样既能体现 Agent Graph，又不会被复杂拓扑限制。

### 3.3 初版模型接入建议

初版接入 3 类模型即可，后续通过配置扩展：

| 模型类型 | 推荐用途 | 说明 |
|---|---|---|
| 原生联网/搜索模型 | Searcher | 负责查询改写、网页搜索、中文信息检索 |
| 高性价比长文本模型 | Reader / Analyzer | 负责长文本阅读、摘要、结构化抽取 |
| 强推理/强写作模型 | Planner / Critic / Writer | 负责任务拆解、审稿、最终报告 |

**重要说明**：系统所有模型均通过 API 调用，不包含任何本地部署的大模型。所有模型配置均支持国产模型 API（如 DeepSeek、智谱AI、月之暗面等），且兼容 OpenAI 接口标准。

工程实现上不要把模型名写死，统一写入 `config/models.yaml`。

---

## 4. 任务类型与拓扑路由

本系统首版支持两种核心拓扑。

### 4.1 拓扑 A：Hierarchical，适合行业报告

**适用场景**：

- 行业研究报告；
- 公司/产品/市场分析；
- 技术趋势报告；
- 竞品分析；
- 有明确结构、有较强事实依赖的问题。

**特点**：

- 先规划，再并行检索和阅读，最后统一分析、审稿、写作；
- 输出结构稳定，适合生成正式报告；
- 成本可控，适合常规 Deep Research 任务。

```text
        Planner
           ↓
     SubQuestion List
           ↓
 ┌─────────┼─────────┐
 ↓         ↓         ↓
Searcher  Searcher  Searcher
 ↓         ↓         ↓
Reader    Reader    Reader
 └─────────┼─────────┘
           ↓
        Analyzer
           ↓
        Critic
           ↓
        Writer
           ↓
      Final Report
```

### 4.2 拓扑 B：Debate，适合开放性问题研究

**适用场景**：

- 开放性研究问题；
- 策略选择问题；
- 争议性观点分析；
- “哪个方案更好”类问题；
- 需要多角度、多模型互相质疑的问题。

**特点**：

- 多个模型或多个 Agent 分支独立形成观点；
- Critic 统一比较分歧、证据强度与逻辑漏洞；
- 更适合非标准答案问题；
- 成本高于拓扑 A，但结论更稳健。

```text
          Planner
             ↓
       Debate Questions
             ↓
 ┌───────────┼───────────┐
 ↓           ↓           ↓
Pro Agent   Con Agent   Neutral Agent
 ↓           ↓           ↓
Evidence    Evidence    Evidence
 └───────────┼───────────┘
             ↓
          Critic
             ↓
        Synthesizer
             ↓
          Writer
             ↓
      Final Research Memo
```

### 4.3 任务到拓扑的路由规则

定义 `TopologyRouter`，根据任务类型选择拓扑。

| 用户问题类型 | 默认拓扑 | 判断关键词 / 特征 |
|---|---|---|
| 行业报告 | Hierarchical | 行业、市场规模、趋势、竞品、商业模式、产业链 |
| 公司分析 | Hierarchical | 公司、财报、产品线、增长、竞争格局 |
| 技术调研 | Hierarchical | 技术路线、框架对比、落地现状 |
| 开放性问题 | Debate | 是否、应该、哪种更好、利弊、可行性 |
| 策略建议 | Debate | 方案选择、路线选择、优先级、决策建议 |
| 高争议问题 | Debate | 争议、反方观点、风险、伦理、监管 |

示例：

```python
class TopologyRouter:
    def route(self, task: TaskSpec) -> str:
        if task.task_type in ["industry_report", "company_analysis", "market_research"]:
            return "hierarchical"
        if task.task_type in ["open_question", "strategy_decision", "controversial_topic"]:
            return "debate"
        return "hierarchical"
```

---

## 5. 领域对象设计

### 5.1 TaskSpec

```python
from pydantic import BaseModel, Field
from typing import Literal

class TaskSpec(BaseModel):
    task_id: str
    user_query: str
    task_type: Literal[
        "industry_report",
        "company_analysis",
        "technical_research",
        "open_question",
        "strategy_decision",
        "general"
    ] = "general"
    language: str = "zh-CN"
    depth: Literal["quick", "standard", "deep"] = "standard"
    budget_level: Literal["low", "medium", "high"] = "medium"
    max_sources: int = 20
    require_citations: bool = True
```

### 5.2 TaskRequirement

Agent 向 Router 声明任务需求。

```python
class TaskRequirement(BaseModel):
    required_capabilities: list[str] = Field(default_factory=list)
    preferred_capabilities: list[str] = Field(default_factory=list)
    preferred_cost_tier: Literal["low", "mid", "high"] = "low"
    max_latency_ms: int | None = None
    complexity: Literal["simple", "medium", "hard"] = "medium"
    min_context_window: int = 8000
```

### 5.3 ModelSpec

```python
class ModelSpec(BaseModel):
    name: str
    provider: str
    api_base: str | None = None
    capabilities: list[str]
    cost_tier: Literal["low", "mid", "high"]
    latency_tier: Literal["fast", "medium", "slow"]
    context_window: int
    strengths: list[str] = []
    weaknesses: list[str] = []
    enabled: bool = True
```

### 5.4 ResearchState

```python
class ResearchState(BaseModel):
    task: TaskSpec
    selected_topology: str | None = None
    plan: list[dict] = []
    sub_results: dict[str, dict] = {}
    debate_results: dict[str, dict] = {}
    analyses: list[dict] = []
    critiques: list[dict] = []
    final_report: dict | None = None

    cost_so_far: float = 0.0
    token_usage: dict[str, int] = {}
    model_usage: dict[str, int] = {}
    audit_trail: list[dict] = []
    errors: list[dict] = []
```

---

## 6. 模型能力池设计

### 6.1 模型注册表

模型配置放入 `config/models.yaml`。

```yaml
models:
  - name: doubao-search
    provider: volcengine
    capabilities:
      - web_search_native
      - chinese
      - multimodal
    cost_tier: low
    latency_tier: fast
    context_window: 128000
    enabled: true

  - name: deepseek-analyzer
    provider: deepseek
    capabilities:
      - chinese
      - long_context
      - code
      - extraction
    cost_tier: low
    latency_tier: medium
    context_window: 64000
    enabled: true

  - name: strong-writer
    provider: openai_or_anthropic
    capabilities:
      - strong_reasoning
      - writing
      - critique
      - synthesis
    cost_tier: high
    latency_tier: medium
    context_window: 128000
    enabled: true
```

### 6.2 模型路由器

Router 接收 `TaskRequirement`，输出 `ModelSpec`。

首版实现四种路由策略：

| 路由器 | 作用 |
|---|---|
| CapabilityRouter | 必须满足 required_capabilities |
| CostAwareRouter | 在满足能力的模型里选择成本最低者 |
| LatencyRouter | 延迟敏感任务优先选择 fast tier |
| FallbackRouter | 主模型失败后自动切换备选模型 |

```python
class BaseRouter:
    async def select_model(self, requirement: TaskRequirement) -> ModelSpec:
        raise NotImplementedError

class CostAwareRouter(BaseRouter):
    async def select_model(self, requirement: TaskRequirement) -> ModelSpec:
        candidates = self.registry.filter_by_capabilities(
            requirement.required_capabilities
        )
        return min(candidates, key=lambda m: self.cost_rank(m.cost_tier))
```

### 6.3 API Key 池

每个模型可以挂多个 Key。

```yaml
api_keys:
  doubao-search:
    - key_id: doubao_key_1
      env_name: DOUBAO_API_KEY_1
      weight: 1
    - key_id: doubao_key_2
      env_name: DOUBAO_API_KEY_2
      weight: 1
```

Key 池需要支持：

1. 加权轮询；
2. 连续失败熔断；
3. 半开探活；
4. 成功率统计；
5. 平均延迟统计；
6. 动态禁用 Key；
7. 不在日志中输出真实 Key。

### 6.4 熔断状态

```python
class KeyStatus(str, Enum):
    HEALTHY = "healthy"
    OPEN = "open"          # 熔断，不再分配请求
    HALF_OPEN = "half_open" # 探活中
    DISABLED = "disabled"
```

---

## 7. Agent 设计

### 7.1 Agent 列表

| Agent | 职责 | 推荐能力需求 | 默认使用场景 |
|---|---|---|---|
| Planner | 拆解问题、生成研究计划 | strong_reasoning | 两种拓扑都需要 |
| Searcher | 查询改写、网页搜索、资料收集 | web_search_native | Hierarchical |
| Reader | 阅读资料、摘要、抽取引用 | long_context, extraction | Hierarchical |
| Analyzer | 跨信源综合、趋势分析、矛盾识别 | reasoning, long_context | Hierarchical |
| Pro Agent | 正方观点研究 | reasoning, web_search_native | Debate |
| Con Agent | 反方观点研究 | reasoning, web_search_native | Debate |
| Neutral Agent | 中立视角研究 | reasoning, long_context | Debate |
| Critic | 审稿、纠错、发现漏洞 | strong_reasoning, critique | 两种拓扑都需要 |
| Writer | 最终报告生成 | writing, synthesis | 两种拓扑都需要 |
| Validator | Schema 校验、引用校验、格式校验 | extraction | 两种拓扑都需要 |

### 7.2 BaseAgent

```python
class BaseAgent:
    name: str
    prompt_template_name: str

    def requirement(self, state: ResearchState) -> TaskRequirement:
        raise NotImplementedError

    async def run(self, state: ResearchState) -> dict:
        requirement = self.requirement(state)
        model = await self.router.select_model(requirement)
        prompt = self.prompt_loader.render(
            template_name=self.prompt_template_name,
            model_name=model.name,
            state=state,
        )
        result = await self.llm_client.invoke(model=model, prompt=prompt)
        return result
```

### 7.3 Agent 输入输出 Schema

每个 Agent 必须有明确输出结构，避免自由文本污染后续流程。

#### Planner 输出

```json
{
  "research_goal": "string",
  "task_type": "industry_report | open_question | general",
  "sub_questions": [
    {
      "id": "sq_1",
      "question": "string",
      "priority": 1,
      "search_queries": ["string"],
      "expected_evidence_type": "market_data | expert_opinion | official_source | news | paper"
    }
  ],
  "suggested_topology": "hierarchical | debate"
}
```

#### Searcher 输出

```json
{
  "sub_question_id": "sq_1",
  "queries_used": ["string"],
  "sources": [
    {
      "title": "string",
      "url": "string",
      "snippet": "string",
      "source_type": "official | media | paper | blog | unknown",
      "publish_date": "string | null",
      "credibility_score": 0.8
    }
  ]
}
```

#### Reader 输出

```json
{
  "sub_question_id": "sq_1",
  "key_findings": ["string"],
  "evidence": [
    {
      "claim": "string",
      "source_url": "string",
      "quote_or_summary": "string",
      "confidence": 0.8
    }
  ],
  "uncertainties": ["string"]
}
```

#### Writer 输出

```json
{
  "title": "string",
  "executive_summary": "string",
  "sections": [
    {
      "heading": "string",
      "content": "string",
      "citations": ["url"]
    }
  ],
  "limitations": ["string"],
  "appendix": "string"
}
```

---

## 8. Prompt 模板系统

### 8.1 目录结构

```text
prompts/
├── planner/
│   ├── v1_basic.zh.j2
│   ├── v2_structured.zh.j2
│   └── dialects/
│       ├── claude.zh.j2
│       ├── gpt.zh.j2
│       └── deepseek.zh.j2
├── searcher/
│   ├── v1_basic.zh.j2
│   └── v2_query_expansion.zh.j2
├── reader/
│   └── v1_extraction.zh.j2
├── analyzer/
│   └── v1_cross_source.zh.j2
├── critic/
│   └── v1_red_team.zh.j2
└── writer/
    ├── industry_report.zh.j2
    └── open_research_memo.zh.j2
```

### 8.2 Prompt 配置

```yaml
agents:
  planner:
    prompt_template: prompts/planner/v2_structured.zh.j2
    output_schema: PlannerOutput

  writer_industry_report:
    prompt_template: prompts/writer/industry_report.zh.j2
    output_schema: WriterOutput

  writer_open_research:
    prompt_template: prompts/writer/open_research_memo.zh.j2
    output_schema: WriterOutput
```

### 8.3 模型方言适配

同一个 Agent 对不同模型加载不同模板：

| 模型类型 | Prompt 风格 |
|---|---|
| Claude | XML 标签、长指令、明确 output format |
| GPT | Markdown 层级结构、角色说明、示例输出 |
| DeepSeek | 中文指令、显式步骤、严格 JSON 输出 |
| 豆包 | 简洁中文指令、少嵌套、直接说明任务 |
| Gemini | 关键约束写入 user message，减少隐含 system 依赖 |

---

## 9. 拓扑 A：行业报告流程设计

### 9.1 输入示例

```json
{
  "query": "请生成一份 2026 年中国 AI Agent 行业发展报告",
  "task_type": "industry_report",
  "depth": "standard",
  "budget_level": "medium"
}
```

### 9.2 流程步骤

1. `Planner` 生成报告大纲与子问题；
2. `Searcher` 并行检索每个子问题；
3. `Reader` 并行阅读资料并抽取证据；
4. `Analyzer` 跨子问题综合分析；
5. `Critic` 检查事实、逻辑、引用与遗漏；
6. 若 Critic 发现重大缺口，回到 Searcher 补充检索；
7. `Writer` 生成最终行业报告；
8. `Validator` 校验结构、引用与输出 Schema；
9. 返回报告和调用统计。

### 9.3 行业报告默认章节

```text
1. 执行摘要
2. 行业定义与研究范围
3. 市场背景与核心驱动力
4. 技术路线与产品形态
5. 产业链与关键参与者
6. 代表性公司 / 产品分析
7. 商业模式与成本结构
8. 竞争格局
9. 风险与不确定性
10. 未来趋势与结论
11. 参考来源
```

### 9.4 关键实现点

- 子问题并发执行；
- 每个子问题独立存储结果；
- Searcher 控制最大搜索源数量；
- Reader 强制保留来源 URL；
- Analyzer 不允许生成无引用的关键判断；
- Critic 可触发一次补充检索；
- Writer 使用行业报告专用模板。

---

## 10. 拓扑 B：开放性研究流程设计

### 10.1 输入示例

```json
{
  "query": "未来两年企业是否应该优先投入多 Agent 系统，而不是单 Agent 工具链？",
  "task_type": "open_question",
  "depth": "deep",
  "budget_level": "high"
}
```

### 10.2 流程步骤

1. `Planner` 将开放性问题拆成争议点；
2. `Pro Agent` 从支持方角度收集证据并形成论证；
3. `Con Agent` 从反对方角度收集证据并形成论证；
4. `Neutral Agent` 从中立角度整理事实边界、适用条件和不确定性；
5. `Critic` 对三方观点做交叉质疑；
6. `Synthesizer` 综合分歧，输出条件化结论；
7. `Writer` 输出开放性研究备忘录；
8. `Validator` 校验引用、结构与不确定性表达。

### 10.3 开放性研究默认结构

```text
1. 问题定义
2. 结论先行：在什么条件下成立
3. 支持方观点与证据
4. 反对方观点与证据
5. 中立事实与约束条件
6. 关键分歧点
7. 风险、反例与不确定性
8. 最终建议
9. 参考来源
```

### 10.4 关键实现点

- 三个分支尽量使用不同模型或不同 Prompt，以降低同质化偏差；
- Pro / Con / Neutral 互不共享中间推理，只共享检索证据；
- Critic 必须指出每一方至少一个弱点；
- Synthesizer 输出条件化结论，而不是单一绝对结论；
- Writer 使用开放性研究 memo 模板。

---

## 11. API 设计

### 11.1 创建研究任务

```http
POST /api/research
```

请求：

```json
{
  "query": "请生成一份中国 AI Agent 行业发展报告",
  "task_type": "industry_report",
  "depth": "standard",
  "budget_level": "medium",
  "max_sources": 20
}
```

响应：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "task_id": "task_abc123",
    "status": "running",
    "selected_topology": "hierarchical"
  }
}
```

### 11.2 查询任务状态

```http
GET /api/research/{task_id}
```

响应：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "task_id": "task_abc123",
    "status": "completed",
    "progress": 100,
    "current_stage": "writer",
    "result": {},
    "metrics": {
      "cost_so_far": 0.42,
      "latency_ms": 81230,
      "model_usage": {
        "doubao-search": 12,
        "deepseek-analyzer": 8,
        "strong-writer": 3
      }
    }
  }
}
```

### 11.3 同步研究接口，演示用

```http
POST /api/research/sync
```

适合本地 Demo，直接等待报告生成并返回结果。

### 11.4 健康检查

```http
GET /health
```

返回 Redis、模型池、搜索服务、Key 池状态。

### 11.5 模型池状态

```http
GET /api/models/status
```

返回每个模型可用性、Key 状态、失败次数、平均延迟。

---

## 12. Redis 数据设计

### 12.1 Key 命名

```text
research:task:{task_id}:state        # ResearchState
research:task:{task_id}:result       # 最终结果
research:task:{task_id}:events       # 事件流
research:cache:{query_hash}          # 查询缓存
model:key:{model_name}:{key_id}      # Key 状态
model:metrics:{model_name}           # 模型调用指标
rate_limit:{user_id}:{minute}        # 限流计数
```

### 12.2 任务状态

```json
{
  "task_id": "task_abc123",
  "status": "running",
  "selected_topology": "hierarchical",
  "current_stage": "reader",
  "progress": 45,
  "updated_at": "2026-05-12T10:00:00Z"
}
```

---

## 13. 目录结构

```text
deep_research_system/
├── app/
│   ├── api/
│   │   ├── routes_research.py
│   │   ├── routes_models.py
│   │   └── routes_health.py
│   ├── agents/
│   │   ├── base.py
│   │   ├── planner.py
│   │   ├── searcher.py
│   │   ├── reader.py
│   │   ├── analyzer.py
│   │   ├── debate.py
│   │   ├── critic.py
│   │   ├── writer.py
│   │   └── validator.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── errors.py
│   │   └── security.py
│   ├── model_pool/
│   │   ├── registry.py
│   │   ├── router.py
│   │   ├── key_pool.py
│   │   ├── circuit_breaker.py
│   │   └── client.py
│   ├── prompts/
│   │   ├── loader.py
│   │   └── renderer.py
│   ├── schemas/
│   │   ├── task.py
│   │   ├── state.py
│   │   ├── model.py
│   │   ├── agent_outputs.py
│   │   └── response.py
│   ├── services/
│   │   ├── research_service.py
│   │   ├── search_service.py
│   │   ├── cache_service.py
│   │   ├── trace_service.py
│   │   └── eval_service.py
│   ├── topology/
│   │   ├── base.py
│   │   ├── router.py
│   │   ├── hierarchical.py
│   │   └── debate.py
│   └── utils/
│       ├── ids.py
│       ├── json.py
│       └── time.py
├── config/
│   ├── models.yaml
│   ├── agents.yaml
│   ├── topology.yaml
│   └── app.yaml
├── prompts/
│   ├── planner/
│   ├── searcher/
│   ├── reader/
│   ├── analyzer/
│   ├── critic/
│   └── writer/
├── tests/
│   ├── test_model_router.py
│   ├── test_key_pool.py
│   ├── test_topology_router.py
│   ├── test_hierarchical.py
│   └── test_debate.py
├── scripts/
│   ├── run_demo.py
│   └── seed_config.py
├── .env.example
├── pyproject.toml
├── README.md
└── main.py
```

---

## 14. 配置文件设计

### 14.1 topology.yaml

```yaml
default_topology: hierarchical

routing_rules:
  industry_report:
    topology: hierarchical
    writer_template: writer/industry_report.zh.j2
  company_analysis:
    topology: hierarchical
    writer_template: writer/industry_report.zh.j2
  technical_research:
    topology: hierarchical
    writer_template: writer/industry_report.zh.j2
  open_question:
    topology: debate
    writer_template: writer/open_research_memo.zh.j2
  strategy_decision:
    topology: debate
    writer_template: writer/open_research_memo.zh.j2

hierarchical:
  max_sub_questions: 6
  max_sources_per_sub_question: 5
  allow_critic_research_loop: true
  max_research_loops: 1

debate:
  branches:
    - pro
    - con
    - neutral
  max_rounds: 1
  require_disagreement_summary: true
```

### 14.2 agents.yaml

```yaml
agents:
  planner:
    required_capabilities: [strong_reasoning]
    preferred_cost_tier: high
    prompt_template: planner/v2_structured.zh.j2

  searcher:
    required_capabilities: [web_search_native]
    preferred_cost_tier: low
    prompt_template: searcher/v2_query_expansion.zh.j2

  reader:
    required_capabilities: [long_context, extraction]
    preferred_cost_tier: low
    prompt_template: reader/v1_extraction.zh.j2

  analyzer:
    required_capabilities: [long_context, reasoning]
    preferred_cost_tier: mid
    prompt_template: analyzer/v1_cross_source.zh.j2

  critic:
    required_capabilities: [strong_reasoning, critique]
    preferred_cost_tier: high
    prompt_template: critic/v1_red_team.zh.j2

  writer:
    required_capabilities: [writing, synthesis]
    preferred_cost_tier: high
    prompt_template: writer/industry_report.zh.j2
```

---

## 15. 开发计划：14 天版本

### Day 1：项目骨架与基础工程

目标：完成可运行的 FastAPI 项目。

任务：

1. 创建项目目录；
2. 配置 Python 虚拟环境；
3. 初始化 `pyproject.toml`；
4. 接入 FastAPI；
5. 实现统一响应结构；
6. 实现全局异常处理；
7. 配置 `.env` 和 `pydantic-settings`；
8. 配置 JSON 日志。

验收：

- `GET /health` 返回正常；
- `GET /docs` 能打开 OpenAPI 页面；
- 错误响应不暴露堆栈。

---

### Day 2：配置系统与 Redis

目标：完成配置驱动基础设施。

任务：

1. 实现 YAML 配置加载器；
2. 加载 `models.yaml`、`agents.yaml`、`topology.yaml`；
3. 接入 Redis；
4. 实现 Redis 单例客户端；
5. 实现缓存服务 `CacheService`；
6. 实现任务状态存储 `TaskStateStore`。

验收：

- 能从配置文件加载模型和 Agent；
- Redis 可读写；
- 任务状态可保存和查询。

---

### Day 3：模型注册表与基础 LLM Client

目标：让系统能通过统一接口调用不同模型。

任务：

1. 实现 `ModelSpec`；
2. 实现 `ModelRegistry`；
3. 实现 `LLMClient` 抽象；
4. 实现 OpenAI-compatible client；
5. 支持从环境变量读取 API Key；
6. 记录调用耗时和 Token 使用量。

验收：

- 能通过统一接口调用至少一个模型；
- 模型调用日志包含 model、latency、token_usage。

---

### Day 4：模型路由器与 Key 池

目标：完成项目核心亮点之一。

任务：

1. 实现 `TaskRequirement`；
2. 实现 `CapabilityRouter`；
3. 实现 `CostAwareRouter`；
4. 实现 `FallbackRouter`；
5. 实现 API Key 加权轮询；
6. 实现 Key 失败计数与熔断状态。

验收：

- Agent 声明能力后 Router 能选出模型；
- 模拟某个 Key 失败后能自动切换；
- 熔断 Key 不再被分配请求。

---

### Day 5：Prompt 模板系统

目标：Prompt 配置化、版本化、可替换。

任务：

1. 引入 Jinja2；
2. 实现 `PromptLoader`；
3. 实现 `PromptRenderer`；
4. 编写 Planner / Searcher / Reader 基础模板；
5. 支持按模型名加载方言模板；
6. 记录 Prompt 版本到 trace。

验收：

- 修改 Prompt 文件即可改变 Agent 行为；
- 每次调用日志记录 prompt_template 与 prompt_version。

---

### Day 6：Agent 基类与 Planner

目标：跑通第一个 Agent。

任务：

1. 实现 `BaseAgent`；
2. 实现 Agent 调用通用流程；
3. 实现 Planner Agent；
4. 定义 Planner 输出 Schema；
5. 实现结构化 JSON 解析与 Pydantic 校验；
6. 失败时自动重试一次。

验收：

- 输入研究问题后，Planner 能输出结构化子问题；
- 输出不符合 Schema 时会自动重试。

---

### Day 7：Searcher 与 Reader

目标：完成资料收集链路。

任务：

1. 实现 Searcher Agent；
2. 接入原生联网模型或 Tavily 作为搜索兜底；
3. 实现查询改写与多 query 扩展；
4. 实现 Reader Agent；
5. Reader 对搜索结果做摘要和证据抽取；
6. 每条证据保留 source_url。

验收：

- 每个子问题能检索到资料；
- Reader 输出 key_findings 与 evidence；
- 所有关键信息保留引用来源。

---

### Day 8：Analyzer、Critic 与 Writer

目标：完成单拓扑所需全部 Agent。

任务：

1. 实现 Analyzer；
2. 实现 Critic；
3. 实现 Writer；
4. 编写行业报告 Writer 模板；
5. 编写开放性研究 Memo 模板；
6. 实现 Validator Agent。

验收：

- Analyzer 能合并多个子问题结果；
- Critic 能输出问题清单；
- Writer 能生成结构化报告。

---

### Day 9：拓扑 A：Hierarchical

目标：行业报告流程端到端跑通。

任务：

1. 实现 `BaseTopology`；
2. 实现 `HierarchicalTopology`；
3. Planner → Searcher 并发 → Reader 并发 → Analyzer → Critic → Writer；
4. 支持 Critic 触发一次补充检索；
5. 实现拓扑执行日志。

验收：

- 输入行业报告题目，自动选择拓扑 A；
- 能生成完整行业报告；
- 并发 Searcher / Reader 正常执行；
- 输出包含 sources、cost、latency。

---

### Day 10：拓扑 B：Debate

目标：开放性问题研究流程端到端跑通。

任务：

1. 实现 `DebateTopology`；
2. 实现 Pro / Con / Neutral 三个 Debate Agent；
3. 实现 Critic 交叉审查；
4. 实现 Synthesizer；
5. Writer 输出开放性研究 memo；
6. 支持 Debate 配置项：分支数量、轮次、模型选择。

验收：

- 输入开放性问题，自动选择拓扑 B；
- 输出支持方、反对方、中立方观点；
- 最终结论有条件、有不确定性、有引用。

---

### Day 11：API 服务与任务状态

目标：把核心流程服务化。

任务：

1. 实现 `ResearchService`；
2. 实现 `POST /api/research`；
3. 实现 `POST /api/research/sync`；
4. 实现 `GET /api/research/{task_id}`；
5. 任务状态写入 Redis；
6. 实现任务事件流记录。

验收：

- 可以通过 HTTP 创建研究任务；
- 可以查询任务状态和结果；
- Demo 时可用同步接口快速展示。

---

### Day 12：Observability 与成本统计

目标：体现工业界工程能力。

任务：

1. 实现 `TraceService`；
2. 记录每个 Agent 的输入、输出摘要、模型、Prompt 版本；
3. 记录 Token、成本、延迟；
4. 统计每个拓扑的成本分布；
5. 实现 `/api/models/status`；
6. 导出 trace JSON。

验收：

- 每次任务能看到完整调用链；
- 能展示“哪个 Agent 花了多少钱”；
- 能比较拓扑 A 和拓扑 B 的成本差异。

---

### Day 13：安全扩展与可靠性

目标：预留 Agent 安全方向亮点。

任务：

1. 实现 Prompt Injection 检测接口空实现；
2. 实现 PII 脱敏接口，可先用正则匹配邮箱、手机号；
3. 实现引用校验：关键 claim 必须有 source；
4. 实现输出 Schema 校验；
5. 实现失败重试与最大重试次数；
6. 实现审计日志。

验收：

- 输出无引用时 Validator 能发现；
- 敏感信息可被脱敏；
- 审计日志记录安全相关事件。

---

### Day 14：Demo、README 与简历材料

目标：项目可演示、可投递。

任务：

1. 准备两个 Demo：
   - 行业报告：走拓扑 A；
   - 开放性问题：走拓扑 B。
2. 编写 README；
3. 编写架构图；
4. 准备 3 分钟演示脚本；
5. 准备简历描述；
6. 准备面试问答。

验收：

- README 能让别人本地跑起来；
- Demo 能展示拓扑路由、模型路由、成本统计；
- 简历描述突出“异构模型协同 Deep Research 框架”。

---

## 16. MVP 范围

### 16.1 必须完成

- 模型注册表；
- 能力路由；
- Key 池与熔断；
- Planner / Searcher / Reader / Analyzer / Critic / Writer；
- 拓扑 A；
- 拓扑 B 简版；
- Prompt 模板系统；
- 任务 API；
- Redis 状态存储；
- 成本与调用日志。

### 16.2 可以延后

- Web 前端；
- LangSmith 接入；
- 复杂多轮 Debate；
- 完整 LLM-as-judge 评测；
- 多租户权限；
- 企业级鉴权；
- 完整 Presidio 脱敏；
- PDF/网页全文抓取高级清洗。

---

## 17. 测试计划

### 17.1 单元测试

| 测试文件 | 测试内容 |
|---|---|
| `test_model_router.py` | 能力匹配、成本优先、Fallback |
| `test_key_pool.py` | 轮询、熔断、半开恢复 |
| `test_prompt_loader.py` | 模板加载、变量渲染、方言适配 |
| `test_topology_router.py` | 任务类型到拓扑映射 |
| `test_validator.py` | Schema 校验、引用校验 |

### 17.2 集成测试

| 测试 | 输入 | 预期 |
|---|---|---|
| 行业报告流程 | “生成 AI Agent 行业报告” | 选择 hierarchical |
| 开放性问题流程 | “企业是否应该优先投入多 Agent？” | 选择 debate |
| Key 失败 | 模拟第一个 Key 报错 | 自动切换 Key |
| Critic 补充检索 | 删除关键引用 | 触发补充检索 |
| 缓存命中 | 重复同一问题 | 第二次直接返回缓存 |

---

## 18. Demo 设计

### 18.1 Demo 1：行业报告

输入：

```text
请生成一份 2026 年中国 AI Agent 行业发展报告，重点关注市场趋势、技术路线、代表性公司和未来风险。
```

展示点：

1. TopologyRouter 选择 Hierarchical；
2. Planner 拆分子问题；
3. Searcher / Reader 并行；
4. Analyzer 汇总；
5. Critic 检查遗漏；
6. Writer 输出行业报告；
7. 显示成本分布。

### 18.2 Demo 2：开放性问题

输入：

```text
未来两年企业是否应该优先建设多 Agent 系统，而不是继续优化单 Agent 工具链？
```

展示点：

1. TopologyRouter 选择 Debate；
2. Pro / Con / Neutral 三分支；
3. Critic 交叉质疑；
4. Synthesizer 输出条件化结论；
5. Writer 输出研究备忘录；
6. 展示 Debate 拓扑成本高但结论更稳健。

---

## 19. README 核心内容

README 建议包含：

```text
1. 项目简介
2. 为什么不是普通多 Agent 检索系统
3. 核心架构图
4. 异构模型路由设计
5. 拓扑 A / 拓扑 B 对比
6. 快速开始
7. 配置说明
8. API 使用示例
9. Demo 示例
10. 可观测性与成本统计
11. 扩展新模型 / 新 Agent / 新拓扑的方法
12. Roadmap
```

---

## 20. 简历描述

### 20.1 一句话版本

设计并实现一个异构模型协同的 Deep Research 框架，通过模型能力路由、Agent 角色拆分与可插拔拓扑编排，在成本约束下自动生成高质量行业报告与开放性研究备忘录。

### 20.2 简历项目描述

- 设计三层解耦架构：模型能力池、Agent 角色层、拓扑编排层，支持模型、Prompt、Agent 与拓扑的配置化扩展。
- 实现异构模型路由器，根据任务能力需求、成本层级、延迟和上下文窗口自动选择模型，使 Searcher / Reader 使用低成本模型，Planner / Critic / Writer 使用强推理模型。
- 实现两类 Deep Research 拓扑：Hierarchical 用于行业报告生成，Debate 用于开放性问题研究，支持并发检索、跨信源分析、批判性审稿与条件化结论生成。
- 构建 API Key 池与熔断机制，支持加权轮询、失败降级、半开探活和调用统计，提高多模型 API 调用的稳定性。
- 接入 Redis 进行任务状态持久化、缓存、限流和调用追踪，记录模型、Prompt 版本、Token、成本、延迟与 Agent 行为审计日志。
- 预留安全与评测扩展点，包括 Prompt Injection 检测、PII 脱敏、引用校验、Schema 校验和 LLM-as-judge 评测接口。

---

## 21. 面试讲法

### 21.1 项目定位怎么讲

这个项目不是简单把多个 Agent 串起来做搜索，而是把 Deep Research 任务拆成不同能力需求，再用模型路由器把不同任务分配给最合适的模型。比如搜索和阅读阶段更看重成本、速度和长上下文，可以用便宜模型；规划、批判性审稿和最终写作更依赖推理和表达，所以用强模型。这样能在成本可控的情况下提升研究报告质量。

### 21.2 拓扑设计怎么讲

我把研究任务分成两类：

- 行业报告这类问题有明确结构，所以使用 Hierarchical 拓扑，先规划、再并发检索阅读、最后统一分析和写作；
- 开放性问题没有标准答案，所以使用 Debate 拓扑，让不同 Agent 从支持、反对、中立视角独立分析，再由 Critic 和 Synthesizer 汇总，输出更稳健的条件化结论。

### 21.3 可扩展性怎么讲

系统所有会变化的部分都配置化，包括模型、Agent、Prompt 和拓扑。新增模型只需要在 `models.yaml` 加能力标签；新增 Agent 只需要继承 `BaseAgent` 并配置 Prompt；新增拓扑只需要继承 `BaseTopology`。核心代码不需要跟着业务场景频繁修改。

---

## 22. 风险与取舍

| 风险 | 影响 | 应对 |
|---|---|---|
| 多模型 API 不稳定 | 任务失败 | Key 池、重试、熔断、Fallback |
| Debate 成本较高 | 不适合所有任务 | 只对开放性/争议性任务启用 |
| 引用不准确 | 报告可信度下降 | Reader 保留 source，Validator 做引用校验 |
| Prompt 效果波动 | 输出质量不稳定 | Prompt 版本管理，保留实验接口 |
| LangGraph 复杂拓扑受限 | Debate 实现困难 | LangGraph + asyncio 混合编排 |
| 搜索结果质量不稳 | 分析偏差 | 多 query 扩展、来源可信度评分、Critic 补充检索 |

---

## 23. 后续 Roadmap

### v0.1：框架跑通

- 单模型调用；
- Planner / Searcher / Writer；
- Hierarchical 简版；
- 同步 API。

### v0.2：异构模型协同

- 模型注册表；
- 能力路由；
- Key 池；
- Reader / Analyzer / Critic。

### v0.3：双拓扑

- Hierarchical 完整版；
- Debate 简版；
- TopologyRouter；
- 两个 Demo。

### v0.4：可观测与安全

- 成本统计；
- Trace 日志；
- 引用校验；
- PII 脱敏；
- Prompt Injection 检测接口。

### v0.5：评测与优化

- LLM-as-judge；
- 引用准确率；
- 成本-质量对比；
- 拓扑 A / B 效果对比。

---

## 24. 最小可演示闭环

如果时间紧，优先做下面这条路径：

```text
FastAPI
  ↓
TaskSpec
  ↓
TopologyRouter
  ↓
HierarchicalTopology / DebateTopology
  ↓
Agent 调用 BaseAgent
  ↓
ModelRouter 选择模型
  ↓
LLMClient 调用模型
  ↓
TraceService 记录成本与延迟
  ↓
Writer 输出报告
```

最小 Demo 必须能展示：

1. 同样是 Deep Research，不同问题会选择不同拓扑；
2. 不同 Agent 会选择不同模型；
3. 系统能输出结构化报告；
4. 系统能展示成本、延迟和模型调用分布；
5. 新增模型或拓扑不需要大改代码。

---

## 25. 项目最终交付物

1. 可运行后端代码；
2. `config/models.yaml`、`config/agents.yaml`、`config/topology.yaml`；
3. Prompt 模板文件；
4. 两个 Demo 脚本；
5. README；
6. 架构图；
7. 简历描述；
8. 面试讲解稿；
9. 成本统计示例；
10. 后续实验接口说明。

