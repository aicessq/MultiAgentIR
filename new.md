
  1. app/schemas/task.py — Added model_slot: str | None field to TaskRequirement
  2. app/model_pool/registry.py — Added get_by_env_slot(slot) method that reads MODEL_{SLOT}_NAME from env and
  looks up the model
  3. app/model_pool/router.py — Added SlotRouter that checks model_slot first, inserted at top of FallbackRouter
  chain
  4. 9 agent files — Each requirement() now includes model_slot=:
    - "reasoning" → planner, critic, pro_agent, con_agent, neutral_agent
    - "search" → searcher, reader
    - "analysis" → analyzer, validator
    - "writing" → writer, synthesizer

  To switch a slot to a different model, just change MODEL_{SLOT}_NAME in .env (e.g.,
  MODEL_SEARCH_NAME=moonshot-v1-8k).

✻ Crunched for 6m 44s

❯ 帮我总结在修改git错误之前的所有实现                                                                            

⏺ 3 Explore agents finished (ctrl+o to expand)
   ├ Explore project structure · 19 tool uses · 0 tokens
   │ ⎿  Done
   ├ Explore core implementation · 32 tool uses · 0 tokens
   │ ⎿  Done
   └ Explore agents and frontend · 58 tool uses · 0 tokens
     ⎿  Done
     
⏺ Deep Research System — 完整实现总结

  一、项目架构

  技术栈: FastAPI + Vue 3 + TypeScript + Tailwind CSS + Element Plus + @vue-flow/core

  核心模式: 多 Agent 协作编排，两种拓扑结构（层级式 / 辩论式），通过 SSE 实时推送进度。

  ---
  二、后端实现
  
  2.1 核心基础设施 (app/core/)

  ┌──────────────────┬────────────────────────────────────────────────────────────────────────────────────────┐
  │       模块       │                                        实现内容                                        │
  ├──────────────────┼────────────────────────────────────────────────────────────────────────────────────────┤
  │                  │ Pydantic-Settings 配置管理，支持 .env + YAML 双源配置；AppConfig 整合 Settings 与      │
  │ config.py        │ models.yaml/agents.yaml/topology.yaml；get_effective_models() 解析 env 变量引用并      │
  │                  │ fallback 到 Settings 默认值；load_dotenv() 填充 os.environ                             │
  ├──────────────────┼────────────────────────────────────────────────────────────────────────────────────────┤
  │ config_loader.py │ Pydantic 校验模型（ModelSpec / AgentConfig / TopologyConfig）；ConfigManager           │
  │                  │ 支持热重载（检测文件 mtime 变化）                                                      │
  ├──────────────────┼────────────────────────────────────────────────────────────────────────────────────────┤
  │ errors.py        │ 12 个自定义异常类（ValidationError / TaskNotFoundError / ModelError 等），统一继承     │
  │                  │ BaseAppError，携带 message/code/status_code/details                                    │
  ├──────────────────┼────────────────────────────────────────────────────────────────────────────────────────┤
  │ logging.py       │ loguru 结构化日志，InterceptHandler 桥接标准 logging，辅助函数 log_request /           │
  │                  │ log_response / log_model_call / log_agent_execution / log_topology_execution           │
  ├──────────────────┼────────────────────────────────────────────────────────────────────────────────────────┤
  │ middleware.py    │ 4 层中间件：RequestID → RequestLogging → ExceptionHandling →                           │
  │                  │ SecurityHeaders；setup_middlewares() 统一注册                                          │
  ├──────────────────┼────────────────────────────────────────────────────────────────────────────────────────┤
  │ redis_client.py  │ 异步 Redis 客户端（ConnectionPool），支持 KV/Hash/List/Set/PubSub/Pipeline             │
  ├──────────────────┼────────────────────────────────────────────────────────────────────────────────────────┤
  │ security.py      │ PII 脱敏（邮箱/手机/身份证）+ Prompt 注入检测                                          │
  └──────────────────┴────────────────────────────────────────────────────────────────────────────────────────┘

  2.2 模型池 (app/model_pool/)

  ┌────────────────────┬──────────────────────────────────────────────────────────────────────────────────────┐
  │        模块        │                                       实现内容                                       │
  ├────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
  │ client.py          │ LLMClient — httpx 异步 HTTP 客户端；支持 OpenAI 兼容 + Anthropic 两种协议；invoke()  │
  │                    │ 非流式调用 + stream() 流式 SSE 调用；StreamResult 收集 usage 统计                    │
  ├────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
  │ registry.py        │ ModelRegistry — 从 models.yaml 加载模型注册表；get_by_env_slot() 从 .env 的          │
  │                    │ MODEL_{SLOT}_NAME 查找模型                                                           │
  ├────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
  │ router.py          │ 5 级路由链：SlotRouter（.env 槽位优先）→ CostAwareRouter（成本偏好）→                │
  │                    │ CapabilityRouter（能力匹配）→ LatencyRouter（延迟优先）；FallbackRouter 串联尝试     │
  ├────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
  │ key_pool.py        │ APIKeyPool — 轮询 API Key 选择，集成 CircuitBreaker；fallback 到 slot-based env      │
  │                    │ vars（MODEL_SEARCH_API_KEY 等）                                                      │
  ├────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
  │ circuit_breaker.py │ KeyCircuitBreaker — 三态熔断器（HEALTHY/HALF_OPEN/OPEN），阈值 3 次失败，60 秒恢复   │
  └────────────────────┴──────────────────────────────────────────────────────────────────────────────────────┘

  2.3 Agent 实现 (app/agents/)
  
  BaseAgent — 统一基类：
  - run(): 选模型 → 流式调用 LLM → 逐 token 发射 agent_stream_token 事件 → 拼接完整响应 → 记录审计 → 解析 JSON →
  发射 agent_output 
  - _parse_output(): 从 LLM 文本中提取第一个 JSON 对象
  - _estimate_cost(): 基于可配置的每 1K token 费率计算成本
  
  ┌──────────────────┬───────────┬───────────────────────────────────────────┬────────────────────────────────┐
  │      Agent       │   槽位    │                   职责                    │              模板              │
  ├──────────────────┼───────────┼───────────────────────────────────────────┼────────────────────────────────┤
  │ PlannerAgent     │ reasoning │ 分解问题为子问题，生成研究计划            │ planner/v2_structured.zh.j2    │
  ├──────────────────┼───────────┼───────────────────────────────────────────┼────────────────────────────────┤
  │ SearcherAgent    │ search    │ 真实网页搜索（Tavily），并行执行多个查询  │ searcher/v3_real_search.zh.j2  │
  ├──────────────────┼───────────┼───────────────────────────────────────────┼────────────────────────────────┤
  │ ReaderAgent      │ search    │ 阅读搜索结果，抽取关键发现和证据          │ reader/v1_extraction.zh.j2     │
  ├──────────────────┼───────────┼───────────────────────────────────────────┼────────────────────────────────┤
  │ AnalyzerAgent    │ analysis  │ 跨信源综合分析，识别趋势/矛盾/缺口        │ analyzer/v1_cross_source.zh.j2 │
  ├──────────────────┼───────────┼───────────────────────────────────────────┼────────────────────────────────┤
  │ CriticAgent      │ reasoning │ 红队审稿，检查事实/逻辑/引用              │ critic/v1_red_team.zh.j2       │
  ├──────────────────┼───────────┼───────────────────────────────────────────┼────────────────────────────────┤
  │ WriterAgent      │ writing   │ 生成结构化研究报告                        │ writer/industry_report.zh.j2   │
  ├──────────────────┼───────────┼───────────────────────────────────────────┼────────────────────────────────┤
  │ ValidatorAgent   │ analysis  │ 代码级校验（无                            │ 无模板                         │
  │                  │           │ LLM），检查标题/摘要/章节/引用            │                                │
  ├──────────────────┼───────────┼───────────────────────────────────────────┼────────────────────────────────┤
  │ DebateAgent      │ reasoning │ 辩论分支（正/反/中立），收集证据形成论点  │ 内置 prompt                    │
  ├──────────────────┼───────────┼───────────────────────────────────────────┼────────────────────────────────┤
  │ SynthesizerAgent │ writing   │ 整合辩论分歧，输出条件化结论              │ analyzer/v1_cross_source.zh.j2 │
  └──────────────────┴───────────┴───────────────────────────────────────────┴────────────────────────────────┘

  2.4 拓扑引擎 (app/topology/)

  层级式 (HierarchicalTopology) — 7 阶段顺序流水线，搜索/阅读阶段并行：
  Planner(10-20%) → Searcher(25-35%) → Reader(45-55%) → Analyzer(60-65%) → Critic(75-80%) → Writer(90-92%) →
  Validator(95-98%) 
  
  辩论式 (DebateTopology) — 适合争议性话题：
  Planner(10-20%) → Pro/Con/Neutral 并行(30-50%) → Critic(55-65%) → Synthesizer(70-75%) → Writer(85-90%) →
  Validator(95-98%) 
  
  TopologyRouter — 根据 task_type 自动选择拓扑（industry_report/technical_research →
  hierarchical；open_question/strategy_decision → debate）

  2.5 服务层 (app/services/)

  ┌─────────────────────┬─────────────────────────────────────────────────────────────────────────────────────┐
  │        服务         │                                      实现内容                                       │
  ├─────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ research_service.py │ 主编排服务；create_task() 异步创建任务 + asyncio.create_task 后台执行；SSE          │
  │                     │ pub/sub（subscribe/unsubscribe/_emit）；内存缓存（MD5 去重）；任务取消支持          │
  ├─────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ search_service.py   │ Tavily API 集成，fallback 到 mock 结果                                              │
  ├─────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ cache_service.py    │ Redis 缓存层，namespace 隔离，可配置 TTL（搜索 30min / 模型 24h）                   │
  ├─────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ task_state_store.py │ Redis 持久化任务状态 + 事件流，支持分页查询/按状态过滤/过期清理                     │
  ├─────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ config_service.py   │ SQLite 持久化模型槽位配置                                                           │
  ├─────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ trace_service.py    │ 内存审计追踪，按模型/Agent 聚合成本                                                 │
  └─────────────────────┴─────────────────────────────────────────────────────────────────────────────────────┘
  
  2.6 API 路由 (app/api/)

  ┌─────────────────────────────────────┬──────────────────────────┐
  │                端点                 │           功能           │
  ├─────────────────────────────────────┼──────────────────────────┤
  │ POST /api/research                  │ 提交研究任务（异步）     │
  ├─────────────────────────────────────┼──────────────────────────┤
  │ POST /api/research/sync             │ 提交研究任务（同步等待） │
  ├─────────────────────────────────────┼──────────────────────────┤
  │ GET /api/research/{task_id}         │ 查询任务状态/结果        │
  ├─────────────────────────────────────┼──────────────────────────┤
  │ POST /api/research/{task_id}/cancel │ 取消任务                 │
  ├─────────────────────────────────────┼──────────────────────────┤
  │ GET /api/research/{task_id}/stream  │ SSE 实时事件流           │
  ├─────────────────────────────────────┼──────────────────────────┤
  │ GET /api/health                     │ 健康检查                 │
  ├─────────────────────────────────────┼──────────────────────────┤
  │ GET /api/health/ready / /live       │ K8s 探针                 │
  ├─────────────────────────────────────┼──────────────────────────┤
  │ GET /api/health/info                │ 系统信息                 │
  ├─────────────────────────────────────┼──────────────────────────┤
  │ GET /api/models/status              │ 模型状态                 │
  ├─────────────────────────────────────┼──────────────────────────┤
  │ GET /api/models/config              │ 槽位配置                 │
  ├─────────────────────────────────────┼──────────────────────────┤
  │ PUT /api/models/config              │ 更新槽位配置             │
  ├─────────────────────────────────────┼──────────────────────────┤
  │ POST /api/models/test               │ 测试模型连接             │
  └─────────────────────────────────────┴──────────────────────────┘

  2.7 Prompt 系统 (prompts/)

  9 个 Jinja2 中文模板，所有模板要求 LLM 输出严格 JSON 格式，定义了字段名、枚举值、分数范围等约束。

  ---
  三、前端实现
  
  3.1 核心页面

  ResearchView.vue — 主研究页：
  - 研究表单（查询输入 + 任务类型 6 选 1 + 深度 3 选 1）
  - 拓扑图可视化（@vue-flow/core，两种布局，节点渐进渲染 + 发光效果）
  - 进度条（带中文阶段名映射）
  - 活动日志（实时时间戳事件列表）
  - 指标卡片（成本/延迟/Token 数/调用次数）
  - 报告查看器（Markdown 渲染，标题/摘要/章节/引用/局限性）
  - 审计追踪表（Element Plus 表格）
  - 导出按钮（Markdown / PDF / Word）
  
  SettingsView.vue — 模型配置页：按槽位编辑模型名/API Base/API Key，支持连接测试

  3.2 状态管理

  research.ts (Pinia Store):
  - submitResearch(): 创建任务 → 开启 SSE EventSource + 2 秒轮询 fallback
  - addEvent(): 处理 SSE 事件，更新节点状态/Agent 详情/流式文本
  - Token 批处理：50ms flush 避免 UI 卡顿
  - 终端事件处理（done/cancelled）：关闭 SSE，停止轮询，设置最终状态
  
  3.3 拓扑可视化

  - 层级式: planner → searcher + reader → analyzer → critic → writer + validator
  - 辩论式: planner → pro + con + neutral → critic → synthesizer → writer
  - 自定义 AgentNode 组件：状态驱动样式（idle/running/completed/error）+ 发光动画
  - DetailPanel：OUTPUT tab（JSON 或流式文本）+ ACTIVITY LOG tab

  3.4 导出功能 (utils/export.ts)

  - exportMarkdown(): 生成 Markdown 文本 Blob 下载
  - exportPdf(): html2pdf.js 渲染
  - exportWord(): docx 库生成，支持标题层级和格式化

  ---
  四、配置体系
  
  .env — 4 个模型槽位

  MODEL_SEARCH_NAME=deepseek-chat     MODEL_SEARCH_API_KEY=sk-xxx
  MODEL_SEARCH_API_BASE=https://api.deepseek.com
  MODEL_ANALYSIS_NAME=deepseek-chat   MODEL_ANALYSIS_API_KEY=sk-xxx
  MODEL_ANALYSIS_API_BASE=https://api.deepseek.com
  MODEL_REASONING_NAME=deepseek-chat  MODEL_REASONING_API_KEY=sk-xxx
  MODEL_REASONING_API_BASE=https://api.deepseek.com
  MODEL_WRITING_NAME=deepseek-chat    MODEL_WRITING_API_KEY=sk-xxx
  MODEL_WRITING_API_BASE=https://api.deepseek.com

  config/ — 4 个 YAML

  - models.yaml: 6 个国产模型（DeepSeek/GLM-4/Kimi/Doubao/ERNIE/Qwen），含能力标签/成本层级/延迟层级
  - agents.yaml: 11 个 Agent 定义（7 核心 + 4 辩论），含能力需求/模板/超时/重试
  - topology.yaml: 拓扑路由规则 + 层级式/辩论式流程定义
  - app.yaml: 应用名/搜索提供商/每模型成本估算

  ---
  五、修复的 Bug 汇总
  
  ┌────────────────────────────┬────────────────────────────────────────────┬────────────────────────────────┐
  │            Bug             │                    根因                    │              修复              │
  ├────────────────────────────┼────────────────────────────────────────────┼────────────────────────────────┤
  │ Illegal header value       │ .env 值不填充 os.environ，os.getenv()      │ config.py 添加 load_dotenv()   │
  │ b'Bearer '                 │ 返回空                                     │                                │
  ├────────────────────────────┼────────────────────────────────────────────┼────────────────────────────────┤
  │ API Base 解析为空          │ get_effective_models() 不 fallback 到      │ 添加 or getattr(self.settings, │
  │                            │ Settings 默认值                            │  env_name, "")                 │
  ├────────────────────────────┼────────────────────────────────────────────┼────────────────────────────────┤
  │ Planner 选择 qwen-max 无   │ deepseek-chat 缺少 strong_reasoning 能力和 │ 更新 models.yaml               │
  │ key                        │  high cost_tier                            │                                │
  ├────────────────────────────┼────────────────────────────────────────────┼────────────────────────────────┤
  │ KeyError("'type'")         │ loguru logger.error(msg, extra={}) 把      │ 改用 logger.bind().error()     │
  │ 中间件崩溃                 │ extra 当 format kwargs                     │                                │
  ├────────────────────────────┼────────────────────────────────────────────┼────────────────────────────────┤
  │ ResponseValidationError    │ 端点声明 -> dict 但返回 ResponseModel      │ 移除返回类型注解               │
  │                            │ Pydantic 对象                              │                                │
  ├────────────────────────────┼────────────────────────────────────────────┼────────────────────────────────┤
  │ Health 端点 500            │ response_model=HealthResponse 与           │ 移除 response_model            │
  │                            │ success_response() 包装不匹配              │                                │
  ├────────────────────────────┼────────────────────────────────────────────┼────────────────────────────────┤
  │ 模型选择不遵循 .env        │ 路由器基于 capabilities 动态选择，忽略     │ 新增 SlotRouter + model_slot   │
  │                            │ .env 槽位                                  │ 字段                           │
  └────────────────────────────┴────────────────────────────────────────────┴────────────────────────────────┘

