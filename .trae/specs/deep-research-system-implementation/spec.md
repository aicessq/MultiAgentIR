# 异构模型协同 Deep Research 系统实现规范

## Why
构建一个可扩展的 Deep Research 系统，在成本约束下通过异构模型路由、Agent 角色拆分与可切换拓扑编排，自动完成高质量深度研究报告生成。该系统旨在解决传统多 Agent 检索系统的同质化模型问题，通过智能路由将不同任务分配给最合适的模型，实现成本与质量的最优平衡。

## What Changes
- 创建完整的三层解耦架构：模型能力池层、Agent 角色层、拓扑编排层
- 实现模型注册表与能力路由系统，支持根据任务需求自动选择模型
- **所有模型均为 API 模型**：系统仅使用 API 调用的大模型服务，不包含任何本地部署的大模型，支持国产模型 API 且兼容 OpenAI 接口
- 实现 API Key 池与熔断机制，提高多模型 API 调用的稳定性
- 实现 Prompt 模板系统，支持版本管理和模型方言适配
- 实现两类核心拓扑：Hierarchical（行业报告）和 Debate（开放性问题研究）
- 实现完整的 Agent 集合：Planner、Searcher、Reader、Analyzer、Critic、Writer、Validator 等
- 实现 Redis 状态存储、缓存、限流和调用追踪
- 实现可观测性系统，记录模型调用、成本、延迟、Token 使用等指标
- **BREAKING**: 所有代码文件必须添加详细的中文注释，包括函数、类、变量、复杂逻辑块及关键算法实现

## Impact
- Affected specs: 模型路由能力、Agent 编排能力、拓扑执行能力、可观测性能力
- Affected code: 整个项目代码库，包括 app/ 目录下的所有模块

## ADDED Requirements
### Requirement: 代码注释规范
所有代码文件（包括但不限于函数、类、变量、复杂逻辑块及关键算法实现）均需添加详细的中文注释。注释内容应清晰说明代码功能、设计思路、参数含义、返回值说明、使用注意事项及关键逻辑解释，确保其他开发人员能够快速理解代码意图和实现细节。

#### Scenario: 函数注释示例
- **WHEN** 开发者编写一个新函数
- **THEN** 函数上方必须包含中文注释，说明函数功能、参数含义、返回值和使用注意事项

### Requirement: 三层架构实现
系统 SHALL 实现三层解耦架构：
1. 模型能力池层：管理模型注册、API Key、熔断、路由
2. Agent 角色层：定义研究角色、Prompt 模板、输入输出 Schema
3. 拓扑编排层：编排 Agent 执行顺序、并行关系与循环逻辑

#### Scenario: 新增模型
- **WHEN** 在 config/models.yaml 中添加新模型配置
- **THEN** 系统能自动识别新模型并在路由时考虑该模型，无需修改核心代码

### Requirement: 异构模型路由
系统 SHALL 根据 Agent 声明的 TaskRequirement（所需能力、成本层级、延迟要求、上下文窗口）自动选择最合适的模型。

#### Scenario: 低成本任务路由
- **WHEN** Searcher Agent 声明需要 web_search_native 能力且偏好低成本
- **THEN** 路由器选择具有 web_search_native 能力且成本层级为 low 的模型

### Requirement: 双拓扑支持
系统 SHALL 支持两种研究拓扑：
1. Hierarchical 拓扑：用于行业报告等结构化研究任务
2. Debate 拓扑：用于开放性问题等争议性研究任务

#### Scenario: 拓扑自动选择
- **WHEN** 用户提交一个行业报告任务
- **THEN** TopologyRouter 自动选择 Hierarchical 拓扑
- **WHEN** 用户提交一个开放性问题
- **THEN** TopologyRouter 自动选择 Debate 拓扑

### Requirement: 可观测性
系统 SHALL 记录每次 LLM 调用的详细信息，包括模型名、Agent、Prompt 版本、耗时、Token 使用量、成本和错误信息。

#### Scenario: 成本统计查看
- **WHEN** 任务执行完成后
- **THEN** 用户可以通过 API 查看每个 Agent 的成本分布和总花费

## MODIFIED Requirements
### Requirement: 现有项目结构
项目将从空目录状态修改为完整的 Deep Research 系统结构，包含 app/、config/、prompts/、tests/ 等目录。

## REMOVED Requirements
无（从零开始构建，无需要移除的现有功能）