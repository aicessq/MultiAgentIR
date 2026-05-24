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

## Bug #8: 开放性问题拓扑中 REPAIR 节点孤立（无连线）

**发现时间**: 2026-05-24

**现象**: 选择"开放性问题"（debate 拓扑）进行研究时，writer 阶段后出现两个孤立的 REPAIR 节点，没有任何连线连接到其他节点

**根因分析**:
- 后端 `debate.py` 的 `execute()` 确实运行了 validator + repair 循环（第 133-177 行），与 hierarchical 拓扑结构一致
- 但前端 `TopologyGraph.vue` 的 `buildDebateLayout()` 只创建了 planner → branches → critic → synthesizer → writer 节点，**缺少 validator 节点**
- `getSubtaskParent()` 对 `repair_writer_N` 返回 `"validator"`，但 validator 不存在于 debate 布局中
- `injectSubtaskEdges()` 中有 `if (!existingNodeIds.has(parent)) continue` 守卫，发现 validator 不在节点列表中，直接跳过边的创建
- 结果：repair_writer_N 节点被创建（`injectSubtaskNodes` 不检查父节点是否存在），但没有边连接到任何节点

**修复方案**:
- `buildDebateLayout()` 增加 `validator` 节点（writer 之后）
- `buildDebateEdges()` 增加 `writer → validator` 边
- 同时增加 `synthesizer → writer` 边（当前缺失）

**修改文件**:
- `frontend/src/components/research/TopologyGraph.vue` — buildDebateLayout 增加 validator，buildDebateEdges 增加 writer→validator 边

---

## Bug #9: REPAIR #2 节点状态不更新（始终显示运行中）

**发现时间**: 2026-05-24

**现象**: 第 2 轮 REPAIR 完成后，拓扑图中 REPAIR #2 节点仍然显示运行状态（未变绿）

**根因分析**:
- 代码追踪确认：后端正确发出 `stage_complete` 事件（`agent: "repair_writer_2"`），store 正确设置 `nodeStates["repair_writer_2"] = "completed"`，`updateDataOnly()` 正确读取并应用状态
- `done` 事件不包含 `agent` 字段，不会修改 `nodeStates`
- 排除代码逻辑问题后，最可能的原因是 **VueFlow 渲染层**：
  - VueFlow 对节点数据使用浅比较，`updateDataOnly()` 中的展开运算符可能没有产生足够不同的引用
  - 或 SSE 连接在 `stage_complete` 和 `done` 之间断开，导致事件丢失
- 需要实际运行调试确认是 VueFlow 渲染问题还是 SSE 传输问题

**修复方案**:
- 在 `updateDataOnly()` 中，对状态变化的节点使用 `triggerRef` 强制 VueFlow 重新渲染
- 或在状态更新时创建完整的节点数组替换（而非原地修改）

**修改文件**:
- `frontend/src/components/research/TopologyGraph.vue` — updateDataOnly() 中增加强制渲染逻辑

---

## Bug #10: 暂停/完成后无法开始新研究

**发现时间**: 2026-05-24

**现象**:
- 研究进行中点击"终止"后，无法重新输入问题开始新研究
- 研究完成后（已生成报告），重新输入问题也无法开始新研究

**根因分析**:

### 原因 A：SSE onerror 不通知 store
`api/research.ts` 第 44 行：`es.onerror = () => es.close()` — 仅关闭 EventSource，不设置 `_sseSource = null`、不重置 `loading`、不更新任务状态。取消任务后 SSE 断连，`onerror` 触发但 store 不知道，`loading` 保持 `true`。

### 原因 B：handleSubmit 无错误处理
`ResearchView.vue` 第 30-34 行：
```typescript
async function handleSubmit(query, taskType, depth) {
  store.reset()
  await store.submitResearch(query, taskType, depth)  // 无 try/catch
}
```
如果 `createResearch` API 调用失败（如后端尚未清理完已取消的任务），错误被静默吞掉，用户无任何反馈。

### 原因 C：提交按钮不反映 loading 状态
`ResearchForm.vue` 第 56 行：`:loading="false"` 硬编码为 false，按钮始终可点击且无加载指示器。用户不知道提交是否生效。

### 原因 D：旧任务的 in-flight poll 覆盖新任务状态
研究完成后开始新研究时，旧任务的 poll 回调可能仍在执行中（已发 HTTP 请求但未返回）。`reset()` 调用 `clearInterval` 不会中止已发出的请求。当旧请求返回时，`currentTask.value = task` 将旧任务数据覆盖到新任务上，导致 UI 显示旧任务的报告。

**修复方案**:
1. `api/research.ts` 的 `streamResearch` 增加 `onerror` 回调参数，通知 store 重置状态
2. `research.ts` 的 `submitResearch` 中 SSE onerror 处理：设置 `_sseSource = null`、`loading = false`
3. `ResearchView.vue` 的 `handleSubmit` 增加 try/catch + `ElMessage.error`
4. `ResearchForm.vue` 的 `:loading` 绑定到 `store.loading`，并增加 `:disabled` 防止重复提交
5. `research.ts` 的 `pollTask` 回调增加 taskId 校验：如果 `currentTask.value?.task_id !== taskId`，跳过本次回调

**修改文件**:
- `frontend/src/api/research.ts` — streamResearch 增加 onError 回调
- `frontend/src/stores/research.ts` — SSE onerror 处理 + poll taskId 校验
- `frontend/src/views/ResearchView.vue` — handleSubmit 增加 try/catch
- `frontend/src/components/research/ResearchForm.vue` — :loading 绑定 store.loading，增加 :disabled

---

## Bug #11: Repair 结束后报告不显示

**发现时间**: 2026-05-24

**现象**: Repair 循环结束后，前端不显示报告内容。report_update 事件在 repair 期间会推送中间版本报告，但只在 writer 结束后短暂显示，repair 开始后消失

**根因分析**:

### 原因 A：done 事件处理器无条件覆盖 result
`research.ts` 第 181-184 行：
```typescript
if (event.type === 'done' && event.result && currentTask.value) {
  currentTask.value.result = event.result   // 直接替换，不保留 report_update 已设置的 report
}
```
`report_update` 事件在 repair 循环中设置了 `currentTask.value.result.report`，但 done 事件到达后用 `event.result` 整体替换。如果后端 done 事件的 result 中 report 为空或结构不同，report 就丢失了。

### 原因 B：in-flight poll 与 done 事件竞争
poll 回调在 `clearInterval` 后仍可能执行（HTTP 请求已发出未返回）。当 poll 回调恢复执行时，`currentTask.value = task` 用 API 返回的数据覆盖 done 事件设置的结果。虽然 poll 有 report 保留逻辑，但只在 `task.result && !task.result.report` 时生效，如果 API 返回了空 report 的 result，保留逻辑不触发。

### 时间线
1. `report_update` 设置 `result.report = 最终报告`
2. `done` 事件到达，`result = event.result`（可能不含 report）→ report 丢失
3. 或 in-flight poll 返回，`currentTask.value = task`（旧数据）→ report 丢失
4. `v-if="report && (status === 'completed')"` → report 为 falsy → 不显示

**修复方案**:
1. done 事件处理器增加 report 保留逻辑（与 poll 一致）：
   ```typescript
   const incoming = event.result
   if (incoming && !incoming.report && currentTask.value?.result?.report) {
     incoming.report = currentTask.value.result.report
   }
   ```
2. poll 回调增加 taskId 校验，防止旧任务 poll 覆盖新任务

**修改文件**:
- `frontend/src/stores/research.ts` — done 事件处理器增加 report 保留 + poll taskId 校验

---

## #12: 过度不确定性传播导致报告空心化

**发现时间**: 2026-05-24

**现象**:
- 生成的报告过度保守，大量章节以"数据不足""无法判断""需要更多研究"等空泛拒绝替代实质性分析
- analyzer 产出的 gaps/missing_evidence 被 critic 和 synthesizer 反复写入正文，同一 gap 在多个章节重复出现
- 缺少精确市场数据（TAM/CAGR）时，整个市场分析章节被跳过而非做定性分析
- research_limitation 类型的发现出现在章节核心论点中，而非局限性区域

**根因分析**:

### 原因 A：claim_type 从未被设置
`AnalyzerClaim.claim_type` 字段存在但默认为 `"general"`，analyzer prompt 未要求 LLM 输出 claim_type。所有 claim 无分类，下游无法区分事实判断、预测判断和研究局限性。

### 原因 B：critic 缺少不确定性路由
critic 只有 severity 分级（critical/high/medium/low），没有"如何处理这个不确定性"的路由。所有 finding 被同等对待，research_limitation 和真正的 blocker 混在一起。

### 原因 C：writer 缺少定性分析框架
writer prompt 没有"证据不足时如何做定性分析"的指令，LLM 倾向于在缺少精确数据时输出"无法判断"。没有硬约束阻止空泛拒绝。

### 原因 D：无硬约束阻止 research_limitation 进入主体章节
report_validator.py 没有检查 claim_type = research_limitation 是否出现在 key_claims 中，也没有检查空章节和 gap 重复。

**修复方案**:

### 1. Claim 分类体系（Schema + Analyzer Prompt）
- 新增 `ClaimType` 枚举：factual_claim / analytical_claim / forecast_claim / risk_claim / research_limitation
- analyzer prompt 要求每个 claim 必须设置 claim_type，并提供分类标准
- research_limitation 类型不得作为章节核心论点，只能进入 limitations/uncertainties
- gaps 输出增加分类：data_gap / source_gap / scope_gap

### 2. Critic 不确定性路由（新 Prompt）
- 新建 `v3_uncertainty_routing.zh.j2` 替代 v2
- 新增 `ResolutionAction` 枚举：blocker / downgrade_required / limitations_only / acceptable_uncertainties
- 每个 finding 必须附带 resolution_action，明确告知 writer 如何处理该不确定性
- 输出增加 uncertainty_summary 统计

### 3. Writer 定性分析框架（Prompt 修改）
- 新增定性分析框架：需求侧信号、供给侧信号、替代指标、商业模式分析、竞争信号
- 禁止空泛拒绝（"无法分析""数据不足"等）
- research_limitation 路由规则：不得出现在 sections[].key_claims 中
- 正向分析要求：每个章节必须有实质内容

### 4. Synthesizer 约束（Prompt 修改）
- 禁止同一 gap 在多个章节重复扩写
- 每个章节必须输出正向分析内容
- research_limitation 只放入 open_questions 或 limitations

### 5. 硬门禁（Validator）
- 新增检查：research_limitation 不得出现在 key_claims
- 新增检查：空章节（< 50 字符且无 key_claims）必须阻断
- 新增检查：同一 gap 不得在多个章节重复出现
- 新增检查：citation dump 检测（citations > 10 且 key_claims < 3）

### 6. 前端适配
- ReportViewer：key_claim 渲染 claim_type 彩色标签（FACT/ANALYSIS/FORECAST/RISK/LIMITATION）
- DetailPanel：analyzer output 显示 claim_type 标签；critic output 显示 resolution_action 标签 + uncertainty_summary
- 后端 result 增加 claim_graph 字段，前端通过 claim_id 查找 claim_type

**修改文件**:
- `app/schemas/agent_outputs.py` — ClaimType 枚举、ResolutionAction 枚举、AnalyzerClaim/CriticFinding 字段更新
- `prompts/analyzer/v2_claim_graph.zh.j2` — claim_type 分类要求、gaps 分类
- `prompts/critic/v3_uncertainty_routing.zh.j2` — **新建**，替代 v2
- `app/agents/critic.py` — 使用 v3 prompt
- `prompts/writer/industry_report.zh.j2` — 定性分析框架、research_limitation 路由、正向分析
- `prompts/writer/open_research_memo.zh.j2` — 同上
- `prompts/debate/synthesizer_v2.zh.j2` — 不确定性处理规则
- `app/validators/report_validator.py` — 4 项新硬门禁
- `app/agents/analyzer.py` — _summarize_output 显示 claim_type 分布
- `app/services/research_service.py` — result 增加 claim_graph
- `frontend/src/api/research.ts` — TaskResult 类型增加 claim_graph
- `frontend/src/views/ResearchView.vue` — claimGraph 计算属性，传递给 ReportViewer
- `frontend/src/components/research/ReportViewer.vue` — claim_type 彩色标签
- `frontend/src/components/research/DetailPanel.vue` — claim_type + resolution_action 显示

---

## 涉及文件总览

| 文件 | Bug # |
|------|-------|
| `app/schemas/model.py` | #4 |
| `app/schemas/agent_outputs.py` | #12 |
| `app/core/config.py` | #4 |
| `app/model_pool/client.py` | #4 |
| `app/agents/analyzer.py` | #12 |
| `app/agents/critic.py` | #12 |
| `app/validators/report_validator.py` | #12 |
| `app/topology/hierarchical.py` | #1, #3, #4, #7 |
| `app/topology/debate.py` | #1, #4, #7 |
| `app/services/research_service.py` | #4, #12 |
| `prompts/analyzer/v2_claim_graph.zh.j2` | #12 |
| `prompts/critic/v3_uncertainty_routing.zh.j2` | #12 |
| `prompts/writer/industry_report.zh.j2` | #12 |
| `prompts/writer/open_research_memo.zh.j2` | #12 |
| `prompts/debate/synthesizer_v2.zh.j2` | #12 |
| `frontend/src/stores/research.ts` | #4, #6, #10, #11 |
| `frontend/src/views/ResearchView.vue` | #5, #10, #12 |
| `frontend/src/api/research.ts` | #10, #12 |
| `frontend/src/components/research/TopologyGraph.vue` | #1, #2, #7, #8, #9 |
| `frontend/src/components/research/DetailPanel.vue` | #1, #7, #12 |
| `frontend/src/components/research/ReportViewer.vue` | #12 |
| `frontend/src/components/research/ProgressBar.vue` | #7 |
| `frontend/src/components/research/ResearchForm.vue` | #10 |
