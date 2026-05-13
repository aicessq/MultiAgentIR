# Tasks

## 第一阶段：项目骨架与基础工程（Day 1）
- [x] 任务 1.1：创建项目目录结构
  - [x] 创建 deep_research_system/ 目录及子目录（app/, config/, prompts/, tests/, scripts/）
  - [x] 创建 main.py 入口文件
  - [x] 创建 pyproject.toml 配置文件
  - [x] 创建 .env.example 环境变量示例文件
  - [x] 创建 README.md 框架

- [x] 任务 1.2：配置 Python 虚拟环境与依赖管理
  - [x] 创建虚拟环境（可选，由用户自行管理）
  - [x] 编写 requirements.txt 或 pyproject.toml 依赖声明
  - [x] 包含 FastAPI、uvicorn、pydantic、httpx、redis、tenacity、jinja2、pyyaml 等核心依赖

- [x] 任务 1.3：实现 FastAPI 基础框架
  - [x] 创建 app/api/ 目录结构
  - [x] 实现统一响应结构（ResponseModel）
  - [x] 实现全局异常处理中间件
  - [x] 实现健康检查端点 GET /health
  - [x] 配置 OpenAPI 文档

- [x] 任务 1.4：配置管理与环境变量
  - [x] 实现基于 pydantic-settings 的配置管理
  - [x] 创建 .env 文件加载支持
  - [x] 实现 JSON 日志配置

## 第二阶段：配置系统与 Redis（Day 2）
- [x] 任务 2.1：实现 YAML 配置加载器
  - [x] 创建 config/ 目录及配置文件模板
  - [x] 实现 YAML 配置加载器，支持 models.yaml、agents.yaml、topology.yaml
  - [x] 实现配置验证与热重载支持

- [x] 任务 2.2：接入 Redis 客户端
  - [x] 实现 Redis 单例客户端
  - [x] 实现连接池管理
  - [x] 实现基础 Redis 操作封装

- [x] 任务 2.3：实现缓存服务
  - [x] 创建 CacheService 类
  - [x] 实现查询缓存功能（research:cache:{query_hash}）
  - [x] 实现缓存过期策略

- [x] 任务 2.4：实现任务状态存储
  - [x] 创建 TaskStateStore 类
  - [x] 实现任务状态保存与查询（research:task:{task_id}:state）
  - [x] 实现任务事件流记录（research:task:{task_id}:events）

## 第三阶段：模型注册表与基础 LLM Client（Day 3）
- [ ] 任务 3.1：实现数据模型（Schemas）
  - [ ] 实现 ModelSpec Pydantic 模型
  - [ ] 实现 TaskRequirement Pydantic 模型
  - [ ] 实现 ResearchState Pydantic 模型
  - [ ] 实现 TaskSpec Pydantic 模型

- [ ] 任务 3.2：实现模型注册表（ModelRegistry）
  - [ ] 创建 ModelRegistry 类
  - [ ] 实现从 models.yaml 加载模型配置
  - [ ] 实现按能力过滤模型的方法
  - [ ] 实现模型启用/禁用状态管理

- [ ] 任务 3.3：实现基础 LLM Client
  - [ ] 创建 LLMClient 抽象基类
  - [ ] 实现 OpenAI-compatible 客户端
  - [ ] 支持从环境变量读取 API Key
  - [ ] 记录调用耗时和 Token 使用量

## 第四阶段：模型路由器与 Key 池（Day 4）
- [ ] 任务 4.1：实现路由器基类与能力路由器
  - [ ] 创建 BaseRouter 抽象类
  - [ ] 实现 CapabilityRouter（必须满足 required_capabilities）
  - [ ] 实现路由器注册机制

- [ ] 任务 4.2：实现成本感知与延迟路由器
  - [ ] 实现 CostAwareRouter（在满足能力的模型里选择成本最低者）
  - [ ] 实现 LatencyRouter（延迟敏感任务优先选择 fast tier）
  - [ ] 实现 FallbackRouter（主模型失败后自动切换备选模型）

- [ ] 任务 4.3：实现 API Key 池
  - [ ] 创建 KeyPool 类
  - [ ] 实现加权轮询分配
  - [ ] 实现 Key 状态管理（HEALTHY, OPEN, HALF_OPEN, DISABLED）
  - [ ] 实现连续失败熔断机制

- [ ] 任务 4.4：实现熔断器与探活机制
  - [ ] 实现 CircuitBreaker 类
  - [ ] 实现半开探活逻辑
  - [ ] 实现成功率与平均延迟统计

## 第五阶段：Prompt 模板系统（Day 5）
- [ ] 任务 5.1：实现 Prompt 加载器
  - [ ] 创建 PromptLoader 类
  - [ ] 基于 Jinja2 实现模板渲染
  - [ ] 支持按模型名加载方言模板

- [ ] 任务 5.2：创建基础 Prompt 模板文件
  - [ ] 创建 prompts/ 目录结构
  - [ ] 编写 Planner 基础模板（v1_basic.zh.j2）
  - [ ] 编写 Searcher 基础模板（v1_basic.zh.j2）
  - [ ] 编写 Reader 基础模板（v1_extraction.zh.j2）

- [ ] 任务 5.3：实现 Prompt 版本管理
  - [ ] 实现模板版本追踪
  - [ ] 记录 Prompt 版本到调用追踪
  - [ ] 支持模板热重载

## 第六阶段：Agent 基类与 Planner（Day 6）
- [ ] 任务 6.1：实现 Agent 基类
  - [ ] 创建 BaseAgent 抽象类
  - [ ] 实现 requirement() 方法声明任务需求
  - [ ] 实现 run() 方法执行 Agent 逻辑
  - [ ] 集成路由器选择模型

- [ ] 任务 6.2：实现 Planner Agent
  - [ ] 创建 PlannerAgent 类
  - [ ] 定义 Planner 输出 Schema
  - [ ] 实现结构化 JSON 解析与 Pydantic 校验
  - [ ] 实现失败自动重试机制

- [ ] 任务 6.3：实现 Agent 输出验证
  - [ ] 创建输出 Schema 验证工具
  - [ ] 实现 JSON 解析错误处理
  - [ ] 实现重试策略配置

## 第七阶段：Searcher 与 Reader（Day 7）
- [ ] 任务 7.1：实现 Searcher Agent
  - [ ] 创建 SearcherAgent 类
  - [ ] 实现查询改写与多 query 扩展
  - [ ] 接入原生联网模型或搜索 API（如 Tavily）
  - [ ] 定义 Searcher 输出 Schema

- [ ] 任务 7.2：实现搜索服务
  - [ ] 创建 SearchService 类
  - [ ] 实现搜索结果去重与排序
  - [ ] 实现来源可信度评分

- [ ] 任务 7.3：实现 Reader Agent
  - [ ] 创建 ReaderAgent 类
  - [ ] 实现文本摘要与证据抽取
  - [ ] 确保每条证据保留 source_url
  - [ ] 定义 Reader 输出 Schema

## 第八阶段：Analyzer、Critic 与 Writer（Day 8）
- [ ] 任务 8.1：实现 Analyzer Agent
  - [ ] 创建 AnalyzerAgent 类
  - [ ] 实现跨信源综合分析
  - [ ] 实现趋势分析与矛盾识别
  - [ ] 定义 Analyzer 输出 Schema

- [ ] 任务 8.2：实现 Critic Agent
  - [ ] 创建 CriticAgent 类
  - [ ] 实现批判性审稿功能
  - [ ] 实现事实校验与逻辑漏洞发现
  - [ ] 定义 Critic 输出 Schema

- [ ] 任务 8.3：实现 Writer Agent
  - [ ] 创建 WriterAgent 类
  - [ ] 实现行业报告模板
  - [ ] 实现开放性研究 Memo 模板
  - [ ] 定义 Writer 输出 Schema

- [ ] 任务 8.4：实现 Validator Agent
  - [ ] 创建 ValidatorAgent 类
  - [ ] 实现 Schema 校验
  - [ ] 实现引用校验
  - [ ] 实现格式校验

## 第九阶段：拓扑 A：Hierarchical（Day 9）
- [ ] 任务 9.1：实现拓扑基类
  - [ ] 创建 BaseTopology 抽象类
  - [ ] 定义拓扑执行接口
  - [ ] 实现拓扑状态管理

- [ ] 任务 9.2：实现 HierarchicalTopology
  - [ ] 创建 HierarchicalTopology 类
  - [ ] 实现 Planner → Searcher 并发 → Reader 并发 → Analyzer → Critic → Writer 流程
  - [ ] 支持 Critic 触发一次补充检索
  - [ ] 实现拓扑执行日志

- [ ] 任务 9.3：实现并发执行机制
  - [ ] 实现 Searcher 并发执行
  - [ ] 实现 Reader 并发执行
  - [ ] 控制最大并发数

## 第十阶段：拓扑 B：Debate（Day 10）
- [ ] 任务 10.1：实现 DebateTopology
  - [ ] 创建 DebateTopology 类
  - [ ] 实现 Pro/Con/Neutral 三个分支并行执行
  - [ ] 实现 Critic 交叉审查
  - [ ] 实现 Synthesizer 整合分歧

- [ ] 任务 10.2：实现 Debate Agents
  - [ ] 创建 ProAgent、ConAgent、NeutralAgent 类
  - [ ] 实现各分支独立研究逻辑
  - [ ] 定义 Debate 分支输出 Schema

- [ ] 任务 10.3：实现 Synthesizer
  - [ ] 创建 SynthesizerAgent 类
  - [ ] 实现条件化结论生成
  - [ ] 实现分歧点总结

## 第十一阶段：API 服务与任务状态（Day 11）
- [ ] 任务 11.1：实现 ResearchService
  - [ ] 创建 ResearchService 类
  - [ ] 实现任务创建与执行流程
  - [ ] 集成拓扑路由器

- [ ] 任务 11.2：实现研究任务 API
  - [ ] 实现 POST /api/research（异步任务创建）
  - [ ] 实现 POST /api/research/sync（同步任务执行）
  - [ ] 实现 GET /api/research/{task_id}（任务状态查询）

- [ ] 任务 11.3：实现任务状态管理
  - [ ] 任务状态写入 Redis
  - [ ] 实现任务事件流记录
  - [ ] 实现进度跟踪

## 第十二阶段：可观测性与成本统计（Day 12）
- [ ] 任务 12.1：实现 TraceService
  - [ ] 创建 TraceService 类
  - [ ] 记录每个 Agent 的输入、输出摘要、模型、Prompt 版本
  - [ ] 记录 Token、成本、延迟

- [ ] 任务 12.2：实现成本统计
  - [ ] 统计每个拓扑的成本分布
  - [ ] 实现成本计算器
  - [ ] 导出 trace JSON

- [ ] 任务 12.3：实现模型状态 API
  - [ ] 实现 GET /api/models/status
  - [ ] 返回每个模型可用性、Key 状态、失败次数、平均延迟

## 第十三阶段：安全扩展与可靠性（Day 13）
- [ ] 任务 13.1：实现安全扩展接口
  - [ ] 实现 Prompt Injection 检测接口（空实现，预留扩展点）
  - [ ] 实现 PII 脱敏接口（正则匹配邮箱、手机号）
  - [ ] 实现审计日志记录安全事件

- [ ] 任务 13.2：增强可靠性
  - [ ] 实现失败重试与最大重试次数配置
  - [ ] 实现输出 Schema 校验增强
  - [ ] 实现引用校验（关键 claim 必须有 source）

## 第十四阶段：Demo、README 与简历材料（Day 14）
- [ ] 任务 14.1：准备 Demo 脚本
  - [ ] 编写行业报告 Demo 脚本
  - [ ] 编写开放性问题 Demo 脚本
  - [ ] 确保 Demo 能展示核心功能

- [ ] 任务 14.2：完善文档
  - [ ] 编写完整的 README.md
  - [ ] 创建架构图
  - [ ] 编写 3 分钟演示脚本

- [ ] 任务 14.3：代码质量与注释完善
  - [ ] 确保所有代码文件添加详细中文注释
  - [ ] 运行代码格式化（black）
  - [ ] 运行 Lint 检查（ruff）
  - [ ] 运行类型检查（mypy）

# Task Dependencies
- [任务 1.1] 是所有后续任务的基础
- [任务 1.3] 依赖 [任务 1.1]
- [任务 2.1] 依赖 [任务 1.1]
- [任务 2.2] 依赖 [任务 1.1]
- [任务 3.1] 依赖 [任务 1.1]
- [任务 3.2] 依赖 [任务 2.1] 和 [任务 3.1]
- [任务 3.3] 依赖 [任务 3.1]
- [任务 4.1] 依赖 [任务 3.2]
- [任务 4.3] 依赖 [任务 3.2]
- [任务 5.1] 依赖 [任务 1.1]
- [任务 5.2] 依赖 [任务 5.1]
- [任务 6.1] 依赖 [任务 3.3]、[任务 4.1] 和 [任务 5.1]
- [任务 6.2] 依赖 [任务 6.1]
- [任务 7.1] 依赖 [任务 6.1]
- [任务 8.1] 依赖 [任务 6.1]
- [任务 9.1] 依赖 [任务 6.1]、[任务 7.1]、[任务 8.1]
- [任务 9.2] 依赖 [任务 9.1]
- [任务 10.1] 依赖 [任务 9.1]
- [任务 11.1] 依赖 [任务 9.2] 和 [任务 10.1]
- [任务 11.2] 依赖 [任务 11.1]
- [任务 12.1] 依赖 [任务 11.1]
- [任务 13.1] 依赖 [任务 11.1]
- [任务 14.1] 依赖 [任务 11.2]
- [任务 14.2] 依赖 [任务 14.1]
- [任务 14.3] 依赖所有代码实现任务