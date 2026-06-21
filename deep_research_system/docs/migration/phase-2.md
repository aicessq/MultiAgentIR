# Phase 2 Migration: Research Branch Subgraph

## 目标
创建 Research Branch Subgraph，处理单个研究子任务，产出可追溯的证据。

## 完成项

### 1. Research Branch State
**文件**: `app/graphs/research_branch/state.py`

轻量、JSON-safe 的 TypedDict：
- `run_id`, `subtask_id`, `question`, `research_round` - 身份标识
- `status`, `current_node` - 状态追踪
- `queries` - 搜索查询列表（append reducer）
- `document_ids` - 文档 ID 列表（merge_unique_strings reducer）
- `evidence_ids` - 证据 ID 列表（merge_unique_strings reducer）
- `source_registry` - 来源注册表（merge_dict reducer）
- `warnings`, `errors` - 警告和错误（append reducer）
- `tokens_used`, `cost_usd` - 预算追踪

关键约束：
- 只存储 ID，不存储完整 artifact
- 所有字段 JSON-safe
- 使用 Annotated reducer 处理并行更新

### 2. Research Branch Nodes
**文件**: `app/graphs/research_branch/nodes.py`

6 个节点：

**plan_queries_node**
- 使用 ModelGateway 生成 3-5 个搜索查询
- 返回 queries 列表
- 失败时 fallback 使用原问题

**execute_search_node**
- 使用 SearchGateway 执行查询
- 返回 search_result_set_id 和 document_ids
- 错误时返回 failed 状态

**fetch_documents_node**
- 使用 DocumentFetcher 抓取 URL
- 返回 documents_fetched 和 documents_failed
- 无 URL 时返回 partial

**extract_evidence_node**
- 从文档中提取证据
- 返回 evidence_ids 和 evidence_count
- 基于 documents_fetched 生成证据

**verify_evidence_node**
- 验证证据质量
- 返回 evidence_validated 和 evidence_rejected
- 无证据时返回 partial

**persist_branch_result_node**
- 持久化最终结果
- 返回最终 status 和 finished_at

关键约束：
- 每个节点只返回增量更新
- 不原地修改共享 state
- 幂等（安全重试）

### 3. Research Branch Builder
**文件**: `app/graphs/research_branch/builder.py`

`ResearchBranchBuilder`：
- 接收 gateways 作为依赖
- `build()` 返回图结构描述
- `run()` 顺序执行节点
- 自动合并增量更新

当前实现为顺序执行，Phase 3 将替换为 LangGraph StateGraph。

### 4. Evidence Validation Pipeline
验证流程：
1. **Quote Verification** - quote 必须在 Document 中定位
2. **Source Tier Check** - 来源必须分类为 TIER_1/2/3
3. **Confidence Validation** - confidence 必须在 0-1 范围
4. **Deduplication** - 相同 quote 只保留一个

当前为简化实现，Phase 3 将完善。

### 5. Fake Providers
使用 Phase 1 的 Fake gateway：
- `FakeModelGateway` - 返回预定义响应
- `FakeSearchGateway` - 返回模拟搜索结果
- `FakeDocumentFetcher` - 返回模拟文档内容
- `InMemoryArtifactStore` - 内存存储

## 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/graphs/research_branch/__init__.py` | 新增 | Branch 模块入口 |
| `app/graphs/research_branch/state.py` | 新增 | Branch State (TypedDict) |
| `app/graphs/research_branch/nodes.py` | 新增 | 6 个节点实现 |
| `app/graphs/research_branch/builder.py` | 新增 | Graph Builder |
| `tests/test_phase2_research_branch.py` | 新增 | Phase 2 测试 |
| `docs/migration/phase-2.md` | 新增 | 本文档 |

## 测试结果

```
89 passed in 0.69s
```

新增 10 个测试用例：
- `TestResearchBranchHappyPath` - 4 个测试
- `TestResearchBranchPartialFailure` - 2 个测试
- `TestResearchBranchIdempotency` - 2 个测试
- `TestResearchBranchState` - 2 个测试

## 关键约束验证

### 1. State JSON-safe
`test_state_is_json_safe` 验证 state 可 JSON 序列化。

### 2. 无 Forbidden Types
`test_state_no_forbidden_types` 验证无 client/connection/session/exception。

### 3. 幂等性
`test_rerun_does_not_duplicate_evidence` 验证重试不重复证据。

### 4. 部分失败处理
`test_search_failure_returns_partial` 验证搜索失败返回 partial。

### 5. 预算追踪
`test_branch_tracks_budget` 验证 token 和 cost 追踪。

## 下一阶段建议 (Phase 3)

### 目标
Hierarchical Graph

### 主要任务
1. **Root State** - 根图状态
2. **Hierarchical Graph** - 层级研究图
3. **Send Fan-out** - 动态并行分支
4. **Reducers** - 状态合并
5. **Analysis/Critique Revision** - 版本管理
6. **Supplemental Research** - 补充研究闭环
7. **Writer/Validator/Repair** - 报告生成和修复
8. **Quality Terminal States** - 质量终态

### 关键约束
- Writer 只消费 authoritative revision
- 并行 branch 不覆盖
- Quality failure 不显示 completed
- 循环严格有上限

### 依赖项
- Phase 2 的 Research Branch
- Phase 1 的 Domain Models
- Phase 1 的 Gateways

## 验收标准
- [x] Research Branch 顺序执行
- [x] State JSON-safe
- [x] 节点幂等
- [x] 部分失败处理
- [x] 预算追踪
- [ ] LangGraph StateGraph 编译（Phase 3）
- [ ] Evidence quote 验证（Phase 3）
- [ ] Checkpoint resume 完整测试（Phase 4）