# Phase 3 Migration: Hierarchical Graph

## 目标
创建 Hierarchical Graph，实现完整的研究流程：并行分支、分析版本、补充研究、报告验证和修复。

## 完成项

### 1. Root State
**文件**: `app/graphs/root/state.py`

根图状态（TypedDict）：
- 身份字段：run_id, thread_id, user_id, query, task_type
- 状态字段：status, current_phase, cancel_requested
- 配置快照：config_snapshot_id, config_hash
- 预算：budget, usage（merge_usage reducer）
- 研究循环：research_round, max_research_rounds, pending_subtasks, completed_subtask_ids
- 证据：evidence_ids（merge_unique_strings）
- 权威指针：authoritative_analysis_id, authoritative_critique_id, authoritative_report_id（override reducer）
- 辩论：debate_round, position_result_refs
- 终端：warnings, errors, terminal_reason

### 2. Shared Reducers
**文件**: `app/graphs/shared/reducers.py`

6 个 reducer：
- `merge_unique_strings` - 合并列表并去重
- `merge_dict` - 合并字典
- `append_list` - 追加列表
- `merge_usage` - 合并使用量计数器
- `merge_branch_results` - 合并分支结果
- `max_int` - 取最大值
- `override` - 直接覆盖

### 3. Hierarchical State
**文件**: `app/graphs/hierarchical/state.py`

层级图状态：
- Wave 追踪：current_wave, max_waves, wave_size
- 子任务：pending_subtasks, completed_subtask_ids, failed_subtask_ids
- 分支结果：branch_results（merge_dict）
- 分析：analysis_revision_id（override）, analysis_revisions
- 批评：critique_revision_id（override）, critique_revisions, critique_findings
- 跟进：followup_queries
- 报告：report_revision_id（override）, report_revisions
- 验证：validation_result, validation_decision
- 修复：repair_instructions, repair_count（max_int）, max_repairs

### 4. Hierarchical Nodes
**文件**: `app/graphs/hierarchical/nodes.py`

13 个节点：

**prepare_research**
- 从查询生成 3 个子任务
- 初始化 wave 追踪

**dispatch_research_wave**
- 按 wave_size 分批派发子任务
- 保留批次供分支执行

**join_research**
- 收集分支结果
- 合并 evidence_ids
- 标记 completed_subtask_ids

**build_analysis**
- 从证据构建分析
- 创建新 analysis_revision_id
- 无证据时返回 failed

**critique**
- 批评分析
- 决定是否需要更多研究
- 受 max_research_rounds 限制

**critique_router**
- 条件路由：generate_followups | write_report

**generate_followups**
- 生成跟进查询
- 创建新子任务
- 递增 research_round

**write_report**
- 从权威分析写报告
- 创建 report_revision_id

**validate_report**
- 验证报告质量
- 返回 score 和 decision

**validation_router**
- 条件路由：finalize_hierarchical | repair_report | quality_gate_failed

**repair_report**
- 修复报告
- 递增 repair_count
- 受 max_repairs 限制

**quality_gate_failed**
- 设置 FAILED_QUALITY_GATE 终态

**finalize_hierarchical**
- 设置 COMPLETED 终态

### 5. Hierarchical Builder
**文件**: `app/graphs/hierarchical/builder.py`

`HierarchicalGraphBuilder`：
- `build()` 返回图结构描述
- `run()` 顺序执行引擎
- 支持 router 分支
- 安全限制：max_steps = 50
- 状态合并：override_keys + list/dict 合并

关键约束：
- Writer 只消费 authoritative_analysis_id
- 补充研究经过完整证据管线
- Quality failure 是独立终态
- 循环有硬限制

### 6. Wave-based Parallel Branches
实现方式：
- `dispatch_research_wave` 按 wave_size 分批
- `research_branch` 节点模拟并行执行
- `join_research` 收集结果
- 支持多轮 wave

## 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/graphs/shared/reducers.py` | 新增 | 共享 reducer |
| `app/graphs/root/state.py` | 新增 | 根图状态 |
| `app/graphs/hierarchical/__init__.py` | 新增 | Hierarchical 模块入口 |
| `app/graphs/hierarchical/state.py` | 新增 | Hierarchical 状态 |
| `app/graphs/hierarchical/nodes.py` | 新增 | 13 个节点 |
| `app/graphs/hierarchical/builder.py` | 新增 | Graph Builder |
| `tests/test_phase3_hierarchical.py` | 新增 | Phase 3 测试 |
| `tests/test_debug.py` | 新增 | 调试用（可删除） |
| `docs/migration/phase-3.md` | 新增 | 本文档 |

## 测试结果

```
102 passed in 0.87s
```

新增 13 个测试用例：
- `TestHierarchicalHappyPath` - 3 个测试
- `TestSupplementalResearch` - 2 个测试
- `TestAuthoritativePointer` - 2 个测试
- `TestReportRepair` - 1 个测试
- `TestQualityGate` - 2 个测试
- `TestLoopLimits` - 1 个测试
- `TestStateJsonSafe` - 1 个测试

## 关键约束验证

### 1. Writer 使用权威分析
`test_writer_uses_authoritative_analysis` 验证 report 引用 analysis。

### 2. 补充研究闭环
`test_supplemental_research_increments_round` 验证 research_round 递增。

### 3. 循环限制
`test_supplemental_research_has_limit` 验证 max_research_rounds 生效。

### 4. 质量门失败
`test_quality_failure_node` 验证 FAILED_QUALITY_GATE 终态。

### 5. 修复限制
`test_repair_loop_respects_max_repairs` 验证 max_repairs 生效。

### 6. 状态 JSON-safe
`test_hierarchical_state_is_json_safe` 验证 JSON 序列化。

## 下一阶段建议 (Phase 4)

### 目标
持久化 Worker 与事件流

### 主要任务
1. **PostgreSQL Migrations** - 数据库表结构
2. **AsyncPostgresSaver** - Checkpointer 实现
3. **Redis Queue/Events** - 任务队列和事件流
4. **Worker** - 独立工作进程
5. **SSE Replay** - 事件重放
6. **Cancel/Resume** - 取消和恢复
7. **Graceful Shutdown** - 优雅关闭

### 关键约束
- API/Worker 可独立扩容
- Worker crash 后可恢复
- SSE 重连不丢关键事件
- 多 API 实例读取同一 Run

### 依赖项
- Phase 3 的 Hierarchical Graph
- Phase 2 的 Research Branch
- Phase 1 的 Domain Models 和 Gateways

## 验收标准
- [x] Hierarchical Graph 顺序执行
- [x] Wave-based 并行分支
- [x] Analysis/Critique 版本管理
- [x] Supplemental research 闭环
- [x] Writer/Validator/Repair 循环
- [x] Quality gate 独立终态
- [x] 循环硬限制
- [ ] LangGraph StateGraph 编译（Phase 4+）
- [ ] PostgreSQL Checkpointer（Phase 4）
- [ ] Redis Streams（Phase 4）
- [ ] Worker 进程（Phase 4）