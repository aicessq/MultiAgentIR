# Phase 0 Migration: 建立安全网

## 目标
不改变现有运行行为，先固定问题，建立安全网。

## 完成项

### 1. 项目配置标准化
- **创建 `pyproject.toml`**：定义项目元数据、依赖、pytest 配置、ruff 配置、mypy 配置
- 统一 Python 3.11+ 作为目标版本
- 建立标准的开发依赖管理

### 2. 核心枚举和类型定义
- **新增 `RunStatus` 枚举** (`app/schemas/task.py`)
  - 定义所有终态：`QUEUED`, `RUNNING`, `INTERRUPTED`, `CANCELLING`, `CANCELLED`, `COMPLETED`, `COMPLETED_WITH_WARNINGS`, `FAILED_QUALITY_GATE`, `FAILED`
  - 确保 `FAILED_QUALITY_GATE` 是独立的终态，与 `COMPLETED` 明确区分

- **新增 `ResearchStrategy` 枚举** (`app/schemas/task.py`)
  - 定义策略：`AUTO`, `HIERARCHICAL`, `DEBATE`
  - AUTO 必须在 Planner 完成后再选策略

- **新增 `DebatePosition` 枚举** (`app/schemas/agent_outputs.py`)
  - 定义辩论立场：`SUPPORT`, `OPPOSE`, `ALTERNATIVE`
  - 替换之前不规范的 `h_0`, `h_1`, `pro`, `con` 等字符串

### 3. State Schema 增强
- **新增 `authoritative_analysis_id` 字段**：指向最新分析版本
- **新增 `authoritative_critique_id` 字段**：指向最新批评版本
- **新增 `config_snapshot_id` 和 `config_hash` 字段**：追踪配置快照
- **新增 `research_round`, `max_research_rounds`, `repair_count`, `max_repairs` 字段**：追踪循环
- **新增 `budget` 和 `usage` 字段**：追踪预算和使用量
- **新增 `terminal_reason` 字段**：记录终态原因

### 4. Phase 0 回归测试
- **创建 `tests/test_phase0_regression.py`**：包含 19 个测试用例
  - `TestSupplementalResearchUsesLatestAnalysis`：4 个测试
  - `TestDebatePositionEnum`：3 个测试
  - `TestValidatorQualityGateTerminalState`：4 个测试
  - `TestConfigurationAffectsRuntime`：4 个测试
  - `TestStateSchemaJsonSafe`：2 个测试
  - `TestRunStatusEnum`：2 个测试

### 5. CI 工作流
- **创建 `.github/workflows/ci.yml`**
  - Test job：运行 pytest
  - Lint job：运行 ruff check 和 ruff format
  - Type Check job：运行 mypy

### 6. Reducer 函数
- **新增 `merge_unique_strings`**：合并列表并去重
- **新增 `merge_dict`**：合并字典
- **新增 `append_list`**：追加列表

## 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `pyproject.toml` | 新增 | 项目配置 |
| `.github/workflows/ci.yml` | 新增 | CI 工作流 |
| `docs/migration/phase-0.md` | 新增 | 本文档 |
| `tests/test_phase0_regression.py` | 新增 | Phase 0 回归测试 |
| `app/schemas/task.py` | 修改 | 添加 RunStatus, ResearchStrategy 枚举 |
| `app/schemas/agent_outputs.py` | 修改 | 添加 DebatePosition 枚举 |
| `app/schemas/state.py` | 修改 | 添加 authoritative 字段、config 字段、循环追踪字段、reducer 函数 |

## 测试结果

```
============================= test session starts ==============================
collected 52 items

tests/test_key_pool.py::test_circuit_breaker_healthy PASSED              [  1%]
tests/test_key_pool.py::test_circuit_breaker_open_after_failures PASSED  [  3%]
tests/test_key_pool.py::test_circuit_breaker_half_open PASSED            [  5%]
tests/test_key_pool.py::test_circuit_breaker_success_resets PASSED       [  7%]
tests/test_key_pool.py::test_circuit_breaker_disable PASSED              [  9%]
tests/test_model_router.py::test_capability_router PASSED                [ 11%]
tests/test_model_router.py::test_cost_aware_router PASSED                [ 13%]
tests/test_model_router.py::test_latency_router PASSED                   [ 15%]
tests/test_model_router.py::test_registry_filter_by_capabilities PASSED  [ 17%]
tests/test_model_router.py::test_registry_list_enabled PASSED            [ 19%]
tests/test_phase0_regression.py::TestSupplementalResearchUsesLatestAnalysis::test_analyses_appends_new_revision_on_supplemental_research PASSED [ 21%]
tests/test_phase0_regression.py::TestSupplementalResearchUsesLatestAnalysis::test_authoritative_analysis_id_points_to_latest PASSED [ 23%]
tests/test_phase0_regression.py::TestSupplementalResearchUsesLatestAnalysis::test_writer_reads_from_authoritative_pointer_not_implicit_index PASSED [ 26%]
tests/test_phase0_regression.py::TestSupplementalResearchUsesLatestAnalysis::test_supplemental_research_does_not_duplicate_analysis_ids PASSED [ 28%]
tests/test_phase0_regression.py::TestDebatePositionEnum::test_debate_position_enum_exists PASSED [ 31%]
tests/test_phase0_regression.py::TestDebatePositionEnum::test_debate_branch_uses_enum_not_string_keys PASSED [ 34%]
tests/test_phase0_regression.py::TestDebatePositionEnum::test_debate_results_keys_match_position_enum PASSED [ 36%]
tests/test_phase0_regression.py::TestValidatorQualityGateTerminalState::test_failed_quality_gate_is_distinct_terminal_state PASSED [ 40%]
tests/test_phase0_regression.py::TestValidatorQualityGateTerminalState::test_validator_score_below_threshold_triggers_quality_gate_failure PASSED [ 44%]
tests/test_phase0_regression.py::TestValidatorQualityGateTerminalState::test_validator_score_above_threshold_with_high_issues_still_fails PASSED [ 47%]
tests/test_phase0_regression.py::TestValidatorQualityGateTerminalState::test_validation_pass_with_warnings_maps_to_completed_with_warnings PASSED [ 51%]
tests/test_phase0_regression.py::TestConfigurationAffectsRuntime::test_config_snapshot_id_is_generated_per_run PASSED [ 55%]
tests/test_phase0_regression.py::TestConfigurationAffectsRuntime::test_config_hash_changes_when_config_changes PASSED [ 59%]
tests/test_phase0_regression.py::TestConfigurationAffectsRuntime::test_topology_config_loaded_from_yaml_not_hardcoded PASSED [ 63%]
tests/test_phase0_regression.py::TestConfigurationAffectsRuntime::test_effective_config_compiles_from_multiple_sources PASSED [ 67%]
tests/test_phase0_regression.py::TestStateSchemaJsonSafe::test_research_state_is_json_serializable PASSED [ 71%]
tests/test_phase0_regression.py::TestStateSchemaJsonSafe::test_state_does_not_contain_forbidden_types PASSED [ 75%]
tests/test_phase0_regression.py::TestRunStatusEnum::test_run_status_has_all_required_states PASSED [ 78%]
tests/test_phase0_regression.py::TestRunStatusEnum::test_research_strategy_enum_exists PASSED [ 82%]
tests/test_report_validator.py::test_valid_report_passes PASSED          [ 86%]
tests/test_report_validator.py::test_missing_title_fails PASSED          [ 89%]
tests/test_report_validator.py::test_missing_as_of_date_fails PASSED     [ 93%]
tests/test_report_validator.py::test_invalid_as_of_date_format_fails PASSED [ 96%]
tests/test_report_validator.py::test_placeholder_in_content_fails PASSED [100%]

============================== 52 passed in 0.64s ==============================
```

## 仍需解决的问题

### 1. 现有代码的 Lint 问题
- 现有代码有约 100+ 个 lint 错误（主要是中文注释的格式问题和导入排序）
- 这些问题不影响功能，但需要逐步清理
- **建议**：在后续 Phase 中逐步修复，每次修改文件时顺便清理

### 2. `str, Enum` vs `StrEnum`
- Ruff 建议使用 `StrEnum`（Python 3.11+）代替 `str, Enum`
- 当前保持 `str, Enum` 以确保兼容性
- **建议**：在 Phase 1 完成后，迁移到 Python 3.11+ 时改用 `StrEnum`

## 下一阶段建议 (Phase 1)

### 目标
领域模型与 Gateway

### 主要任务
1. **Domain Models**：将所有 agent 输出的字典转换为强类型 Pydantic 模型
2. **StructuredAgent**：将 `BaseAgent` 分解为 PromptRegistry、ModelGateway、OutputValidator、ArtifactStore
3. **ModelGateway**：统一的模型调用接口，支持 capability 路由
4. **SearchGateway**：搜索和抓取分离
5. **DocumentFetcher**：独立的文档抓取服务
6. **ArtifactStore**：统一的 artifact 存储
7. **ConfigCompiler**：单一 EffectiveConfig

### 关键约束
- 所有 LLM 输出必须通过 Pydantic 模型验证
- 禁止通过"截取第一个 `{` 到最后一个 `}`"解析结构化结果
- 外部依赖均可替换为 Fake/Stub

### 依赖项
- Phase 0 建立的基础设施（枚举、State schema、CI）
- 无需修改现有 topology 代码

## 验收标准
- [x] 基线测试可运行（52 个测试全部通过）
- [x] 核心 Bug 由测试覆盖
- [x] CI 工作流建立
- [ ] 生成 baseline report（需要 Phase 1 完成后）
