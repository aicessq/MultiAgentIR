# 系统架构与技术栈学习指南

本文档帮助你快速理解 MultiAgentIR 项目的实现方法，适合想要学习、二次开发或面试准备的开发者。

---

## 重要说明：为什么不用 LangGraph？

本项目 **没有使用 LangGraph**，而是自己实现了一套拓扑编排系统。原因：

1. **更灵活的控制流** — 自研拓扑支持复杂的并行子任务、修复循环、补充检索循环，这些在 LangGraph 中实现较复杂
2. **更透明的事件流** — 每个阶段都能精确控制 SSE 事件发送，前端可以实时看到每个 Agent 的思考过程
3. **更轻量** — 不依赖额外的框架，代码更易理解和调试
4. **学习价值更高** — 自己实现编排逻辑，面试时能讲清楚原理

核心实现文件：
- `app/topology/base.py` — 拓扑基类，事件发送
- `app/topology/hierarchical.py` — 层级式拓扑（并行子任务 + 修复循环）
- `app/topology/debate.py` — 辩论式拓扑
- `app/topology/router.py` — 任务类型 → 拓扑路由

---

## 1. 系统分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                    前端层 (Vue 3)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ ResearchView│  │ TopologyGraph│  │ ReportViewer│          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         └────────────────┼────────────────┘                 │
│                          ↓                                  │
│                   Pinia Store                               │
│                   (SSE 事件路由)                             │
└─────────────────────────────────────────────────────────────┘
                           ↓ SSE
┌─────────────────────────────────────────────────────────────┐
│                    API 层 (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ routes_research.py                                    │   │
│  │ - POST /research         创建任务                      │   │
│  │ - GET /research/{id}/stream  SSE 实时事件流            │   │
│  │ - GET /research/{id}     轮询状态                      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    服务层 (Services)                         │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ ResearchService │  │ SearchService   │                  │
│  │ - 任务生命周期   │  │ - Tavily API    │                  │
│  │ - SSE pub/sub   │  │ - 搜索结果缓存  │                  │
│  └────────┬────────┘  └─────────────────┘                  │
└───────────┼─────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────────────────┐
│                    拓扑层 (Topology)                         │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ Hierarchical    │  │ Debate          │                  │
│  │ - 层级式编排    │  │ - 辩论式编排    │                  │
│  │ - 并行子任务    │  │ - 多观点并行    │                  │
│  │ - 修复循环      │  │ - 综合分析      │                  │
│  └────────┬────────┘  └────────┬────────┘                  │
│           └────────────────────┼───────────────────────────│
│                                ↓                            │
│                         TopologyRouter                      │
│                         (任务类型 → 拓扑选择)                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    Agent 层 (Agents)                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ Planner │ │ Searcher│ │ Reader  │ │ Analyzer│           │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘           │
│       └───────────┼───────────┼───────────┘                │
│                   ↓           ↓                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                       │
│  │ Critic  │ │ Writer  │ │Validator│                       │
│  └─────────┘ └─────────┘ └─────────┘                       │
│                                                              │
│  所有 Agent 继承 BaseAgent:                                  │
│  - run() → 选择模型 → 流式调用 → 解析输出 → 发送事件        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    模型池层 (Model Pool)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ModelRegistry│  │FallbackRouter│  │ APIKeyPool │         │
│  │ - 模型配置  │  │ - 能力路由   │  │ - Key 管理 │         │
│  │ - 能力标签  │  │ - 成本权衡   │  │ - 熔断隔离 │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                          ↓                                  │
│                     LLMClient                               │
│                     (流式调用 + 重试)                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 核心技术实现

### 2.1 并行子任务执行

**文件**: `app/topology/hierarchical.py`

```python
# 每个子问题独立实例化 Searcher/Reader
searcher_tasks = []
for sq in state.plan:
    sq_id = sq["id"]
    agent_name = f"searcher_{sq_id}"  # 如 searcher_sq_1
    searcher = self.searcher_cls()    # 新实例
    sq_state = state.model_copy(deep=True)
    sq_state.plan = [sq]
    
    # 包装事件回调，让子任务有独立的节点名
    wrapped_on_event = _wrap_agent_name(on_event, agent_name)
    searcher_tasks.append(searcher.run(sq_state, on_event=wrapped_on_event))

# 并行执行
search_results = await asyncio.gather(*searcher_tasks, return_exceptions=True)
```

**关键点**:
- `searcher_cls = lambda: SearcherAgent(...)` — 工厂函数，每次调用返回新实例
- `_wrap_agent_name()` — 包装事件回调，让 `searcher_sq_1` 等子任务在前端有独立节点
- `asyncio.gather()` — 并行执行所有子任务

---

### 2.2 SSE 实时事件流

**后端** (`app/services/research_service.py`):

```python
class ResearchService:
    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
    
    def subscribe(self, task_id: str) -> asyncio.Queue:
        """前端订阅任务事件"""
        queue = asyncio.Queue()
        self._subscribers[task_id].append(queue)
        return queue
    
    def _emit(self, task_id: str, event: dict):
        """推送事件到所有订阅者"""
        for queue in self._subscribers.get(task_id, []):
            queue.put_nowait(event)
```

**前端** (`frontend/src/stores/research.ts`):

```typescript
// 打开 SSE 连接
_sseSource = streamResearch(task.task_id, (event) => {
  addEvent(event)  // 路由事件到对应状态
}, () => {
  // 连接断开回调
})

// 事件路由
function addEvent(event: any) {
  if (event.type === 'stage_start') {
    nodeStates.value[event.agent] = 'running'
  } else if (event.type === 'agent_stream_token') {
    // Token 流缓冲，50ms 刷新一次
    _tokenBuffer[event.agent] = (_tokenBuffer[event.agent] || '') + event.token
  } else if (event.type === 'done') {
    currentTask.value = event.result
  }
}
```

---

### 2.3 自动修复循环

**文件**: `app/topology/hierarchical.py`

```python
# Writer → Validator → (若不合格) 重新 Writer
max_repair_attempts = 2
for attempt in range(max_repair_attempts):
    # 运行 Writer
    writer_result = await self.writer.run(state, on_event=...)
    state.final_report = writer_result
    
    # 运行 Validator
    validator_result = await self.validator.run(state, on_event=None)  # 不发送事件
    
    if validator_result.get("score", 0) >= 85:
        break  # 通过
    
    # 未通过，准备修复上下文
    state.repair_context = {
        "issues": validator_result.get("issues", []),
        "attempt": attempt + 1,
    }
```

**关键点**:
- Validator 返回 `score` 和 `issues`
- 若 `score < 85`，将 `issues` 放入 `repair_context`，让 Writer 下一轮修复
- 修复时 Validator 的 `on_event=None`，避免覆盖 `repair_writer` 节点状态

---

### 2.4 补充检索循环

**文件**: `app/topology/hierarchical.py`

```python
# Critic 发现信息不足时触发
critic_result = await self.critic.run(state, on_event=on_event)

if critic_result.get("needs_more_research"):
    # 用 Critic 建议的查询重新搜索
    supplementary_queries = critic_result.get("suggested_queries", [])
    
    # 运行补充搜索
    searcher = self.searcher_cls()
    search_result = await searcher.run(...)
    
    # 重新分析 → 重新审稿
    state = await self.analyzer.run(state, ...)
    state = await self.critic.run(state, ...)
```

---

### 2.5 Agent 基类设计

**文件**: `app/agents/base.py`

```python
class BaseAgent:
    name: str = "base"
    prompt_template_name: str = ""
    
    def requirement(self, state: ResearchState) -> TaskRequirement:
        """声明模型需求（子类重写）"""
        return TaskRequirement()
    
    async def run(self, state: ResearchState, on_event: Callable = None) -> dict:
        # 1. 选择模型
        requirement = self.requirement(state)
        model = await self.router.select_model(requirement)
        
        # 2. 加载 Prompt 模板
        prompt = self.prompt_loader.render(self.prompt_template_name, context)
        
        # 3. 流式调用 LLM
        async for chunk in self.llm_client.stream(model, prompt):
            # 发送 token 事件
            self._emit(on_event, {"type": "agent_stream_token", "token": chunk})
        
        # 4. 解析 JSON 输出
        parsed = self._parse_output(full_response)
        
        # 5. 发送输出事件
        self._emit(on_event, {"type": "agent_output", "output": parsed})
        
        return parsed
```

**子类示例** (`app/agents/planner.py`):

```python
class PlannerAgent(BaseAgent):
    name = "planner"
    prompt_template_name = "planner/v3_hypothesis.zh.j2"
    
    def requirement(self, state: ResearchState) -> TaskRequirement:
        return TaskRequirement(
            model_slot="reasoning",           # 使用推理槽位
            required_capabilities=["strong_reasoning"],
            preferred_cost_tier="high",       # 高成本可接受
            complexity="hard",
        )
```

---

### 2.6 模型路由

**文件**: `app/model_pool/router.py`

```python
class FallbackRouter:
    async def select_model(self, requirement: TaskRequirement) -> ModelConfig:
        """根据需求选择最合适的模型"""
        candidates = self.registry.get_by_capability(requirement.required_capabilities)
        
        # 按成本排序
        if requirement.preferred_cost_tier == "low":
            candidates = sorted(candidates, key=lambda m: m.cost_per_1k)
        
        # 检查 Key 健康状态
        for model in candidates:
            if self.key_pool.is_healthy(model.name):
                return model
        
        return None  # 无可用模型
```

---

## 3. 前端关键实现

### 3.1 拓扑图可视化

**文件**: `frontend/src/components/research/TopologyGraph.vue`

```vue
<script setup lang="ts">
import { VueFlow, useVueFlow } from '@vue-flow/core'

// 节点用 ref + watch，不用 computed（保留拖拽位置）
const nodes = ref<Node[]>([])
const edges = ref<Edge[]>([])

// 监听 nodeStates 变化，动态注入子任务节点
watch(() => props.nodeStates, (states) => {
  const newNodes: Node[] = []
  
  // 基础节点
  newNodes.push({ id: 'planner', position: { x: 0, y: 0 }, ... })
  
  // 动态子任务节点
  for (const [agent, status] of Object.entries(states)) {
    if (agent.startsWith('searcher_sq_')) {
      const sqId = agent.replace('searcher_sq_', '')
      newNodes.push({
        id: agent,
        position: { x: 100 * parseInt(sqId), y: 100 },  // 避免碰撞
        ...
      })
    }
  }
  
  nodes.value = newNodes
}, { immediate: true })
</script>
```

---

### 3.2 报告渲染

**文件**: `frontend/src/components/research/ReportViewer.vue`

```vue
<template>
  <div class="report">
    <!-- 关键主张 -->
    <section v-for="claim in report.key_claims" :key="claim.claim_id">
      <h3>{{ claim.statement }}</h3>
      <span class="type">{{ claim.claim_type }}</span>
      <div class="evidence">
        <a v-for="ref in claim.evidence_refs" :href="getSourceUrl(ref)">
          {{ ref }}
        </a>
      </div>
    </section>
    
    <!-- 风险登记 -->
    <section v-if="report.risk_register?.length">
      <h2>风险与不确定性</h2>
      <ul>
        <li v-for="risk in report.risk_register">{{ risk }}</li>
      </ul>
    </section>
  </div>
</template>
```

---

## 4. 配置系统

### 4.1 模型配置 (`config/models.yaml`)

```yaml
models:
  - name: deepseek-chat
    api_base: ${MODEL_SEARCH_API_BASE}
    api_key: ${MODEL_SEARCH_API_KEY}
    capabilities:
      - web_search
      - long_context
    cost_per_1k_input: 0.001
    cost_per_1k_output: 0.002
    
  - name: deepseek-reasoner
    api_base: ${MODEL_REASONING_API_BASE}
    api_key: ${MODEL_REASONING_API_KEY}
    capabilities:
      - strong_reasoning
    cost_per_1k_input: 0.01
    cost_per_1k_output: 0.02
```

### 4.2 拓扑配置 (`config/topology.yaml`)

```yaml
hierarchical:
  max_sub_questions: 5
  max_repair_attempts: 2
  enable_supplementary_search: true
  
debate:
  max_debate_branches: 3
  max_repair_attempts: 2
```

### 4.3 Prompt 模板 (`prompts/planner/v3_hypothesis.zh.j2`)

```jinja2
你是一个研究规划专家。用户的问题是：
{{ state.task.query }}

请将这个问题拆解为 3-5 个子问题，每个子问题应该：
1. 聚焦于一个具体的研究维度
2. 可以通过网页搜索获得事实依据
3. 避免与其他子问题重叠

输出格式：
{
  "sub_questions": [
    {"id": "sq_1", "question": "...", "focus": "..."},
    ...
  ]
}
```

---

## 5. 数据模型

### 5.1 全局状态 (`app/schemas/state.py`)

```python
class ResearchState(BaseModel):
    task: TaskSpec
    plan: list[dict] = []              # Planner 输出
    sub_results: dict[str, dict] = {}  # Searcher/Reader 结果
    analyses: list[dict] = []          # Analyzer 输出
    critiques: list[dict] = []         # Critic 输出
    final_report: dict = {}            # Writer 输出
    repair_context: dict = {}          # 修复上下文
    errors: list[dict] = []            # 错误记录
    
    current_stage: str = ""
    progress: int = 0
```

### 5.2 声明类型 (`app/schemas/agent_outputs.py`)

```python
class ClaimType(str, Enum):
    factual_claim = "factual_claim"         # 事实陈述
    analytical_claim = "analytical_claim"   # 分析结论
    forecast_claim = "forecast_claim"       # 预测判断
    risk_claim = "risk_claim"               # 风险提示
    research_limitation = "research_limitation"  # 研究局限

class ResolutionAction(str, Enum):
    blocker = "blocker"                     # 阻塞问题
    downgrade_required = "downgrade_required"  # 需降级处理
    limitations_only = "limitations_only"   # 仅限局限性
    acceptable_uncertainties = "acceptable_uncertainties"  # 可接受不确定性
```

---

## 6. 学习路径建议

### 入门（理解整体）

1. 阅读 `README.md` 了解项目定位
2. 运行项目，观察前端拓扑图变化
3. 打开浏览器开发者工具，查看 SSE 事件流

### 进阶（理解实现）

1. **后端入口**: `main.py` → `app/api/routes_research.py`
2. **服务层**: `app/services/research_service.py` 的 `_execute()` 方法
3. **拓扑编排**: `app/topology/hierarchical.py` 的 `execute()` 方法
4. **Agent 基类**: `app/agents/base.py` 的 `run()` 方法
5. **模型路由**: `app/model_pool/router.py` 的 `select_model()` 方法

### 深入（理解细节）

1. **并行子任务**: 搜索 `_wrap_agent_name` 和 `asyncio.gather`
2. **修复循环**: 搜索 `repair_context` 和 `max_repair_attempts`
3. **补充检索**: 搜索 `needs_more_research`
4. **SSE 事件**: 搜索 `stage_start` 和 `agent_stream_token`
5. **前端状态**: 阅读 `frontend/src/stores/research.ts`

---

## 7. 面试常见问题

**Q: 并行子任务怎么实现的？**
A: 每个子问题独立实例化 Agent，用 `asyncio.gather` 并行执行。事件通过 `_wrap_agent_name` 包装，让子任务在前端有独立节点。

**Q: SSE 怎么保证实时性？**
A: 后端用 `asyncio.Queue` 做 pub/sub，前端用 `EventSource` 接收。Token 流在客户端 50ms 缓冲刷新，避免高频渲染。

**Q: 修复循环怎么避免无限循环？**
A: 配置 `max_repair_attempts = 2`，最多修复 2 次。Validator 返回 `score`，低于 85 才触发修复。

**Q: 异构模型路由怎么实现的？**
A: Agent 通过 `requirement()` 声明需求（能力、成本、复杂度），`FallbackRouter` 根据需求从 `ModelRegistry` 选择最合适的模型。

**Q: 前端拓扑图怎么动态更新？**
A: `nodeStates` 是响应式的，watch 它的变化动态生成节点数组。子任务节点通过命名约定（`searcher_sq_1`）自动注入。

---

## 8. 扩展指南

### 新增 Agent

1. 在 `app/agents/` 创建 `my_agent.py`，继承 `BaseAgent`
2. 在 `prompts/my_agent/` 创建 Prompt 模板
3. 在拓扑中调用：`my_agent = MyAgent(router, llm_client, key_pool)`

### 新增拓扑

1. 在 `app/topology/` 创建 `my_topology.py`，继承 `BaseTopology`
2. 实现 `execute(state, on_event)` 方法
3. 在 `TopologyRouter` 中添加路由规则

### 新增模型

1. 在 `.env` 添加模型配置
2. 在 `config/models.yaml` 注册模型，声明能力标签
3. 系统自动路由，无需改代码
