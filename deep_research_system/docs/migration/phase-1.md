# Phase 1 Migration: 领域模型与 Gateway

## 目标
建立强类型领域模型和统一的外部依赖接口，为 LangGraph 重构奠定基础。

## 完成项

### 1. Domain Layer
创建了完整的领域层：

**Enums (`app/domain/enums.py`)**
- `RunStatus` - 9 种终态（含 `FAILED_QUALITY_GATE`）
- `ResearchStrategy` - AUTO, HIERARCHICAL, DEBATE
- `DebatePosition` - SUPPORT, OPPOSE, ALTERNATIVE
- `ArtifactType` - PLAN, ANALYSIS_REVISION, REPORT_REVISION 等
- `ClaimType` - FACTUAL, ANALYTICAL, FORECAST, RISK, LIMITATION
- `ErrorCategory` - TRANSIENT, RATE_LIMIT, AUTH, INVALID_OUTPUT 等
- `QualityDecision` - PASS, REPAIR, HUMAN_REVIEW, FAIL
- `SourceTier` - TIER_1, TIER_2, TIER_3, UNKNOWN

**Errors (`app/domain/errors.py`)**
- 错误分类体系，支持 retry routing
- `TransientError` - 可重试
- `InvalidOutputError` - 不可重试
- `BudgetExceededError` - Policy 错误
- `ModelUnavailableError` - 模型不可用
- `SearchProviderError` - 搜索失败
- `FetchError` - 抓取失败

**Models (`app/domain/models/__init__.py`)**
- `RevisionMeta` - 不可变版本元数据
- `Source` - 搜索来源
- `Document` - 抓取文档
- `Evidence` - 证据（必须来自 Document passage）
- `Claim` - 论点（关联 Evidence IDs）
- `Artifact` - 基类
- `PlanArtifact` - 研究计划
- `AnalysisRevision` - 分析版本
- `CritiqueRevision` - 批评版本
- `ReportRevision` - 报告版本
- `ValidationResult` - 验证结果

### 2. Gateways
创建了统一的外部依赖接口：

**ModelGateway (`app/gateways/model/`)**
- `ModelRequest` - 模型调用请求（含 output_schema）
- `ModelResponse` - 模型响应（含 parsed_output）
- `ModelGateway` - 抽象接口
- `DefaultModelGateway` - 默认实现
- `FakeModelGateway` - 测试用

关键约束：
- 所有 structured output 必须通过 Pydantic 验证
- 禁止 raw brace slicing
- Required capabilities 必须满足
- Budget 检查在调用前执行
- Repair attempts 有界（max 2）

**SearchGateway (`app/gateways/search/`)**
- `SearchQuery` - 搜索查询
- `SearchResult` - 搜索结果（URL/snippet，不含全文）
- `SearchGateway` - 抽象接口
- `DefaultSearchGateway` - 默认实现（含 dedup、domain classification）
- `FakeSearchGateway` - 测试用

关键约束：
- SearchGateway 只返回 URL 和 snippet
- DocumentFetcher 负责全文抓取
- Domain classification 支持 TIER_1/2/3

**DocumentFetcher (`app/gateways/fetch/`)**
- `FetchRequest` - 抓取请求
- `FetchResult` - 抓取结果
- `DocumentFetcher` - 抽象接口
- `DefaultDocumentFetcher` - 默认实现（含 SSRF 保护）
- `FakeDocumentFetcher` - 测试用

关键约束：
- SSRF 保护（禁止 private IP、localhost、metadata endpoint）
- Content size limit
- Timeout per URL

**ArtifactStore (`app/gateways/storage/`)**
- `ArtifactStore` - 抽象接口
- `InMemoryArtifactStore` - 内存存储（测试用）
- `FileArtifactStore` - 文件存储（开发用）

关键约束：
- Artifacts 不可变
- Revision chain tracking
- Authoritative pointer 支持

### 3. Config
创建了单一配置真相：

**EffectiveConfig (`app/config/effective_config.py`)**
- `GraphConfig` - Graph 设置（recursion_limit, max_research_rounds）
- `ConcurrencyConfig` - 并发限制
- `TimeoutConfig` - 超时设置
- `BudgetConfig` - 预算限制
- `QualityConfig` - 质量门设置
- `ModelCatalogEntry` - 模型目录条目
- `EffectiveConfig` - 冻结配置快照
- `ConfigCompiler` - 配置编译器
- `FakeConfigCompiler` - 测试用

关键约束：
- 运行时只读取一个 EffectiveConfig
- 配置冻结后不受后续修改影响
- Config hash 用于验证

### 4. StructuredAgent
创建了强类型 Agent 基类：

**StructuredAgent (`app/agents/structured_agent.py`)**
- `PromptRegistry` - Prompt 注册和版本管理
- `OutputValidator` - 输出验证（禁止 brace slicing）
- `StructuredAgent` - 抽象基类

关键约束：
- 所有输出通过 Pydantic 验证
- 禁止截取第一个 `{` 到最后一个 `}`
- Repair attempts 有界
- 失败返回错误，不返回假数据

## 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/domain/__init__.py` | 新增 | Domain layer 入口 |
| `app/domain/enums.py` | 新增 | 所有枚举定义 |
| `app/domain/errors.py` | 新增 | 错误分类体系 |
| `app/domain/models/__init__.py` | 新增 | Pydantic 模型 |
| `app/gateways/__init__.py` | 新增 | Gateways 入口 |
| `app/gateways/model/__init__.py` | 新增 | Model gateway 入口 |
| `app/gateways/model/spec.py` | 新增 | Model request/response spec |
| `app/gateways/model/gateway.py` | 新增 | ModelGateway 实现 |
| `app/gateways/search/__init__.py` | 新增 | Search gateway 入口 |
| `app/gateways/search/spec.py` | 新增 | Search request/result spec |
| `app/gateways/search/gateway.py` | 新增 | SearchGateway 实现 |
| `app/gateways/fetch/__init__.py` | 新增 | Fetch gateway 入口 |
| `app/gateways/fetch/spec.py` | 新增 | Fetch request/result spec |
| `app/gateways/fetch/gateway.py` | 新增 | DocumentFetcher 实现 |
| `app/gateways/storage/__init__.py` | 新增 | Storage gateway 入口 |
| `app/gateways/storage/artifact_store.py` | 新增 | ArtifactStore 实现 |
| `app/config/__init__.py` | 新增 | Config 入口 |
| `app/config/effective_config.py` | 新增 | EffectiveConfig 实现 |
| `app/agents/structured_agent.py` | 新增 | StructuredAgent 实现 |
| `tests/test_phase1_components.py` | 新增 | Phase 1 测试 |
| `docs/migration/phase-1.md` | 新增 | 本文档 |

## 测试结果

```
79 passed in 0.77s
```

新增 27 个测试用例：
- `TestDomainEnums` - 4 个测试
- `TestDomainErrors` - 3 个测试
- `TestDomainModels` - 5 个测试
- `TestModelGateway` - 2 个测试
- `TestSearchGateway` - 2 个测试
- `TestDocumentFetcher` - 2 个测试
- `TestArtifactStore` - 1 个测试
- `TestEffectiveConfig` - 3 个测试
- `TestStructuredAgent` - 3 个测试
- `TestNoMockSources` - 2 个测试

## 关键约束验证

### 1. 禁止 Raw Brace Slicing
`OutputValidator` 使用 `json.JSONDecoder.raw_decode()` 而不是截取 `{` 到 `}`。

### 2. 禁止 Mock Sources
Fake gateway 用于测试，生产 gateway 返回真实数据或错误。

### 3. Required Capabilities 严格生效
`ModelGateway.select_model()` 必须满足所有 required capabilities。

### 4. Budget 检查
`ModelGateway.check_budget()` 在调用前检查。

### 5. SSRF 保护
`DocumentFetcher.is_url_allowed()` 禁止 private IP 和 metadata endpoint。

### 6. Evidence 来自 Document
`Evidence` 模型必须关联 `document_id` 和 `passage_id`。

### 7. Revision Chain
`RevisionMeta.supersedes_revision_id` 支持版本链追踪。

## 下一阶段建议 (Phase 2)

### 目标
Research Branch Subgraph

### 主要任务
1. **Branch State** - 研究 branch 的轻量 State
2. **Branch Nodes** - plan_queries, execute_search, fetch_documents, extract_evidence
3. **Evidence Validation** - quote 必须能在 Document 中定位
4. **Fake Provider** - 完整的测试 Provider
5. **Checkpoint Resume Tests** - 恢复时不重复抓取

### 关键约束
- Evidence quote 必须验证
- Provider 失败返回 partial/failed
- 恢复时不重复副作用

### 依赖项
- Phase 1 的 Domain Models
- Phase 1 的 Gateways
- Phase 1 的 Config

## 验收标准
- [x] Domain models 全部 Pydantic 化
- [x] Gateways 有 Fake 实现
- [x] Config 单一真相
- [x] StructuredAgent 禁止 brace slicing
- [x] 所有测试通过
- [ ] 现有 Agent 迁移到 StructuredAgent（Phase 2）
- [ ] Evidence 验证闭环（Phase 2）