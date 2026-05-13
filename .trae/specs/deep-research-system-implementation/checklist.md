# 验证检查清单

## 代码质量与注释
- [ ] 所有代码文件均添加了详细的中文注释，包括函数、类、变量、复杂逻辑块及关键算法实现
- [ ] 注释内容清晰说明代码功能、设计思路、参数含义、返回值说明、使用注意事项及关键逻辑解释
- [ ] 代码通过 black 格式化，风格统一
- [ ] 代码通过 ruff lint 检查，无严重警告
- [ ] 代码通过 mypy 类型检查，类型注解完整

## 项目结构与基础工程
- [ ] 项目目录结构完整，包含 deep_research_system/、app/、config/、prompts/、tests/、scripts/ 等目录
- [ ] main.py 入口文件存在且可启动 FastAPI 应用
- [ ] pyproject.toml 配置文件包含所有必要依赖
- [ ] .env.example 文件提供环境变量示例
- [ ] GET /health 端点返回正常状态
- [ ] GET /docs 能打开 OpenAPI 文档页面
- [ ] 全局异常处理中间件能捕获异常并返回统一错误响应

## 配置系统与 Redis
- [ ] config/models.yaml、config/agents.yaml、config/topology.yaml 配置文件存在且格式正确
- [ ] YAML 配置加载器能正确加载和验证配置文件
- [ ] Redis 客户端能正常连接并执行基本操作
- [ ] CacheService 能实现查询缓存功能
- [ ] TaskStateStore 能保存和查询任务状态

## 模型注册表与 LLM Client
- [ ] ModelSpec、TaskRequirement、ResearchState、TaskSpec 等数据模型定义完整
- [ ] ModelRegistry 能从 models.yaml 加载模型配置
- [ ] ModelRegistry 支持按能力过滤模型
- [ ] LLMClient 抽象基类定义完整
- [ ] OpenAI-compatible 客户端能调用模型 API
- [ ] 模型调用记录耗时和 Token 使用量

## 模型路由器与 Key 池
- [ ] BaseRouter 抽象类定义完整
- [ ] CapabilityRouter 能根据 required_capabilities 选择模型
- [ ] CostAwareRouter 能在满足能力的模型中选择成本最低者
- [ ] FallbackRouter 能在主模型失败后自动切换备选模型
- [ ] KeyPool 实现加权轮询分配
- [ ] KeyPool 实现熔断机制（HEALTHY, OPEN, HALF_OPEN, DISABLED 状态）
- [ ] CircuitBreaker 实现半开探活逻辑

## Prompt 模板系统
- [ ] PromptLoader 能加载 Jinja2 模板
- [ ] PromptRenderer 能渲染模板并注入变量
- [ ] 支持按模型名加载方言模板
- [ ] prompts/ 目录包含 Planner、Searcher、Reader 等基础模板
- [ ] 模板版本能记录到调用追踪中

## Agent 系统
- [ ] BaseAgent 抽象类定义完整，包含 requirement() 和 run() 方法
- [ ] PlannerAgent 能输出结构化子问题列表
- [ ] PlannerAgent 输出符合定义的 JSON Schema
- [ ] SearcherAgent 能执行搜索并返回结构化结果
- [ ] ReaderAgent 能对搜索结果进行摘要和证据抽取，保留 source_url
- [ ] AnalyzerAgent 能进行跨信源综合分析
- [ ] CriticAgent 能进行批判性审稿和事实校验
- [ ] WriterAgent 能生成行业报告和开放性研究备忘录
- [ ] ValidatorAgent 能进行 Schema 校验和引用校验

## 拓扑系统
- [ ] BaseTopology 抽象类定义完整
- [ ] HierarchicalTopology 实现完整流程：Planner → Searcher 并发 → Reader 并发 → Analyzer → Critic → Writer
- [ ] HierarchicalTopology 支持 Critic 触发补充检索
- [ ] DebateTopology 实现 Pro/Con/Neutral 三个分支并行执行
- [ ] DebateTopology 包含 Critic 交叉审查和 Synthesizer 整合分歧
- [ ] 拓扑执行日志记录完整

## API 服务
- [ ] POST /api/research 能创建异步研究任务
- [ ] POST /api/research/sync 能同步执行研究任务并返回结果
- [ ] GET /api/research/{task_id} 能查询任务状态和结果
- [ ] 任务状态能正确写入 Redis
- [ ] 任务事件流记录完整

## 可观测性与成本统计
- [ ] TraceService 能记录每个 Agent 的输入、输出摘要、模型、Prompt 版本
- [ ] TraceService 能记录 Token 使用量、成本和延迟
- [ ] GET /api/models/status 能返回每个模型可用性、Key 状态、失败次数、平均延迟
- [ ] 成本统计能展示每个拓扑的成本分布
- [ ] trace JSON 能导出完整调用链信息

## 安全扩展与可靠性
- [ ] Prompt Injection 检测接口预留（空实现）
- [ ] PII 脱敏接口能识别邮箱、手机号等敏感信息
- [ ] 审计日志能记录安全相关事件
- [ ] 失败重试机制能正常工作
- [ ] 引用校验能发现无来源的关键 claim

## Demo 与文档
- [ ] 行业报告 Demo 脚本能正常运行并展示核心功能
- [ ] 开放性问题 Demo 脚本能正常运行并展示核心功能
- [ ] README.md 完整，包含项目简介、架构图、快速开始、配置说明、API 使用示例等
- [ ] 架构图清晰展示三层解耦架构
- [ ] 3 分钟演示脚本能有效展示项目亮点