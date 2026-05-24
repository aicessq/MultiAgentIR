# Bug 修复记录

---

## Bug #1: 补充研究阶段卡死 + 子任务节点只显示最后一个

**发现时间**: 2026-05-23

**现象**:
- 前端拓扑图中，`supplementary_search` 节点进入运行状态后永远卡在 "running"
- 多个并行 searcher 子任务的事件全部映射到同一个 "searcher" 节点，前端只显示最后一个子问题的输出

**根因分析**:
1. `hierarchical.py` 中补充研究阶段（Critic→Searcher 循环）内部调用的 searcher、analyzer、critic agent 发出的事件使用各自的 agent 名称（如 "searcher"、"analyzer"），这些事件会覆盖父级 `supplementary_search` 节点的状态，导致状态混乱
2. 并行 searcher 子任务全部发出 `agent: "searcher"` 的事件，前端无法区分不同子任务

**修复方案**:
- 新增 `_wrap_agent_name(on_event, wrapped_name)` 函数，包装事件回调，将内部 agent 级别事件（`agent_model_selected`、`agent_thinking`、`agent_output`、`agent_stream_token`、`subtask_complete`）的 agent 字段重命名为指定名称
- 补充研究阶段内部所有 agent 事件统一包装为 `supplementary_search`
- 每个并行 searcher 子任务使用唯一名称 `searcher_{sq_id}`，通过 `_wrap_agent_name` 包装事件

**修改文件**:
- `app/topology/hierarchical.py` — 新增 `_wrap_agent_name()`，重构补充研究循环和并行 searcher/reader
- `app/topology/debate.py` — 从 hierarchical 导入 `_wrap_agent_name`
- `frontend/src/components/research/TopologyGraph.vue` — 新增 `injectSubtaskNodes()`/`injectSubtaskEdges()` 动态创建子任务节点
- `frontend/src/components/research/DetailPanel.vue` — 扩展 isSearcher/isReader 匹配子任务模式（`searcher_sq_\d+`）

---

## Bug #2: 子节点互相重叠

**发现时间**: 2026-05-23

**现象**: 多个 searcher_sq_1、reader_sq_1 等子节点在拓扑图中重叠显示，无法区分

**根因分析**:
`computeSubtaskPosition()` 使用固定偏移量定位子节点，没有检测与已有节点的碰撞

**修复方案**:
- 新增碰撞检测函数 `overlaps(x, y, existingNodes)`，定义节点尺寸常量 `NODE_W=180`, `NODE_H=70`, `NODE_PAD=12`
- `computeSubtaskPosition()` 从父节点偏移开始，沿 Y 轴向下逐行搜索，直到找到不与任何已有节点重叠的位置

**修改文件**:
- `frontend/src/components/research/TopologyGraph.vue` — 新增 `overlaps()`、调整 `computeSubtaskPosition()` 逻辑

---

## Bug #3: Reader 输出在前端没有显示

**发现时间**: 2026-05-23

**现象**: reader agent 执行完毕后，前端 DetailPanel 中没有 output 内容

**根因分析**:
`hierarchical.py` 中 reader 阶段对每个子任务只发出了 `stage_complete` 事件，但没有携带 `output` 字段

**修复方案**:
- reader 阶段对每个子任务发出 `stage_complete` 时附加 `output` 字段（与 searcher 阶段保持一致）

**修改文件**:
- `app/topology/hierarchical.py` — reader 阶段 `stage_complete` 事件增加 `output`

---

## Bug #4: Repair 结束后前端状态不更新 + 最终报告为空

**发现时间**: 2026-05-23

**现象**:
- repair_writer 节点完成校验后，前端仍显示 "修复写作中"
- 下载的最终报告为空（`{}` 或内容缺失）

**根因分析（状态不更新）**:
- `_execute()` 中 `on_topology_event` 回调会将 `event["agent"]` 设置为 `current_stage`
- repair 循环内 validator 使用原始 `on_event` 运行，发出的 `stage_complete` 事件将 `current_stage` 覆盖为 "validator"
- 但 repair_writer 的 `stage_complete` 事件 `current_stage` 从未被设为 "completed"

**根因分析（报告为空）**:
- `_stream_openai()` 请求体中**没有 `max_tokens` 字段**，DeepSeek 默认限制为 8192 tokens
- Writer 生成完整行业报告时输出恰好达到 8192 tokens，JSON 被截断
- `_parse_output()` 无法从截断的 JSON 中提取有效内容，返回 `{}` 或 `{"raw_content": "..."}`
- 3 次 writer 调用（1 次初始 + 2 次 repair）全部在 8192 tokens 处截断

**修复方案**:

### 状态更新修复
- `research_service.py` 的 done 事件增加 `current_stage: "completed"`
- `research.ts` store 的 done 事件处理中读取 `event.current_stage` 并更新
- repair 循环内 validator 使用 `on_event=None` 运行，避免覆盖 repair_writer 状态

### 报告为空修复（3 处改动）
1. **`app/schemas/model.py`**: `ModelSpec` 增加 `max_tokens: int = 8192` 字段
2. **`app/core/config.py`**: `DEEPSEEK_MAX_TOKENS` 默认值从 8192 改为 16384
3. **`app/model_pool/client.py`**: `_stream_openai()` 和 `_call_openai_compatible()` 请求体增加 `"max_tokens": model.max_tokens`

config 已有的 `max_tokens_env` 解析逻辑（`get_effective_models()` 第 279 行）会自动将 `DEEPSEEK_MAX_TOKENS` 环境变量解析到 `ModelSpec.max_tokens`，registry 的字段过滤（`registry.py` 第 17 行）会自动包含新字段。

**修改文件**:
- `app/schemas/model.py` — ModelSpec 增加 max_tokens 字段
- `app/core/config.py` — DEEPSEEK_MAX_TOKENS 默认值 8192 → 16384
- `app/model_pool/client.py` — 两处请求体增加 max_tokens
- `app/services/research_service.py` — done 事件增加 current_stage
- `app/topology/hierarchical.py` — repair 循环内 validator 使用 on_event=None
- `app/topology/debate.py` — 同上
- `frontend/src/stores/research.ts` — done 事件处理读取 current_stage

---

## Bug #7: 第二轮 REPAIR 前端不渲染

**发现时间**: 2026-05-24

**现象**:
- 最多允许 2 轮 REPAIR，但前端拓扑图只显示第 1 轮 REPAIR 节点活动
- 第 2 轮 REPAIR 执行时，REPAIR 节点状态没有更新回 "running"

**根因分析**:
- 两轮 REPAIR 的后端事件完全相同：`stage_start`/`stage_complete` 的 `agent` 都是 `"repair_writer"`，`progress` 都是 96/97
- 前端 store 处理 `stage_complete` 后将 `nodeStates["repair_writer"]` 设为 `"completed"`
- 第 2 轮 `stage_start` 虽然会将状态设回 `"running"`，但由于事件完全相同，前端无法区分是第几轮
- 拓扑图中的 REPAIR 是静态节点，与动态子任务节点（`searcher_sq_*`）的处理逻辑不同
- 且日志无法确认 validator 是否真的触发了第 2 轮（可能第 1 轮后就通过了校验）

**修复方案**:
1. 后端：每轮 REPAIR 使用唯一 agent 名称 `repair_writer_{N}`（N 从 1 开始），事件增加 `repair_count` 字段
2. 前端 TopologyGraph：移除静态 `repair_writer` 节点，改为动态注入（与 `searcher_sq_*` 相同机制）
3. 前端 TopologyGraph：`getSubtaskParent()` 增加 `repair_writer_\d+` → `validator` 映射
4. 前端 TopologyGraph：REPAIR 节点需要双向边（validator ↔ repair_writer_N）
5. 前端 DetailPanel：`isWriter` 匹配 `repair_writer_\d+`，`getAgentLabel` 生成 "REPAIR #N" 标签
6. 前端 ProgressBar：`getStageLabel` 匹配 `repair_writer_\d+` 显示 "修复写作中 #N"
7. 后端日志：repair 循环增加 validator 结果日志，便于确认是否触发了多轮

**修改文件**:
- `app/topology/hierarchical.py` — repair 循环使用 `repair_writer_{N}` 命名，增加 validation 日志
- `app/topology/debate.py` — 同上
- `frontend/src/components/research/TopologyGraph.vue` — 移除静态 repair_writer 节点，动态注入 repair_writer_N 节点，双向边
- `frontend/src/components/research/DetailPanel.vue` — isWriter 匹配 `repair_writer_\d+`，getAgentLabel 支持 REPAIR #N
- `frontend/src/components/research/ProgressBar.vue` — getStageLabel 支持 repair_writer_\d+

---

## Bug #5: 下载按钮在 Repair 阶段就出现

**发现时间**: 2026-05-23

**现象**: repair 还在进行中时，前端已显示"下载报告"按钮和报告内容区域

**根因分析**:
- `ResearchView.vue` 中报告区域和下载按钮使用 `v-if="report"` 判断
- `report_update` 事件在 repair 过程中就会推送中间版本报告到前端
- report 对象存在后 `v-if="report"` 立即为 true，此时任务尚未完成

**修复方案**:
- 报告区域和下载按钮的显示条件改为 `v-if="report && (store.currentTask.status === 'completed' || store.currentTask.status === 'failed')"`

**修改文件**:
- `frontend/src/views/ResearchView.vue` — 下载按钮和报告区域增加 status 判断

---

## Bug #6: Poll 覆盖 report_update 推送的报告

**发现时间**: 2026-05-23

**现象**: report_update 推送的中间报告在下一次 poll 后消失

**根因分析**:
- `research.ts` 中 `pollTask()` 每 2 秒调用 `getResearch(taskId)` 获取任务状态
- 响应中 `currentTask.value = task` 直接替换整个任务对象
- 如果 API 返回的 result 中 report 为空，会覆盖 report_update 已设置的报告内容

**修复方案**:
- 在 poll 合并逻辑中增加：如果新 result 存在但 report 为空，而旧 result 有 report，保留旧 report

**修改文件**:
- `frontend/src/stores/research.ts` — pollTask() 增加 report 保留逻辑

---

## 涉及文件总览

| 文件 | Bug # |
|------|-------|
| `app/schemas/model.py` | #4 |
| `app/core/config.py` | #4 |
| `app/model_pool/client.py` | #4 |
| `app/topology/hierarchical.py` | #1, #3, #4, #7 |
| `app/topology/debate.py` | #1, #4, #7 |
| `app/services/research_service.py` | #4 |
| `frontend/src/stores/research.ts` | #4, #6 |
| `frontend/src/views/ResearchView.vue` | #5 |
| `frontend/src/components/research/TopologyGraph.vue` | #1, #2, #7 |
| `frontend/src/components/research/DetailPanel.vue` | #1, #7 |
| `frontend/src/components/research/ProgressBar.vue` | #7 |
