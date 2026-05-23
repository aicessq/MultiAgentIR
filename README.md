[English](README_EN.md) | **中文**

<div align="center">

# MultiAgentIR

**异构模型协同 Deep Research 系统**

基于 FastAPI + LangGraph 的多 Agent 智能检索分析框架，通过异构模型路由、Agent 角色拆分与可切换拓扑编排，自动完成高质量深度研究报告生成。

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-1C3C3C.svg)](https://github.com/langchain-ai/langgraph)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 系统架构

<div align="center">
  <img src="fig/fig1.png" alt="System Architecture" width="800"/>
</div>

---

## 核心亮点

- **异构模型协同** — 不同 Agent 根据能力需求自动路由到不同模型，低成本模型铺量，强模型把关
- **双拓扑编排** — 行业报告走层级式拓扑（Hierarchical），开放性问题走辩论式拓扑（Debate），可插拔扩展
- **配置驱动** — 新增模型、Agent、Prompt、拓扑时尽量不改核心代码，统一 YAML 配置管理
- **工程化可观测** — 全链路记录模型调用、成本、延迟、Token 与审计日志
- **安全扩展** — 预留 Prompt Injection 检测、PII 脱敏、审计追踪、引用校验等接口

---

## 拓扑编排

### 拓扑 A：Hierarchical（行业报告）

适合有明确结构、强事实依赖的研究任务（行业分析、竞品调研、技术趋势）：

```
        Planner
           ↓
     SubQuestion List
           ↓
 ┌─────────┼─────────┐
 ↓         ↓         ↓
Searcher  Searcher  Searcher
 ↓         ↓         ↓
Reader    Reader    Reader
 └─────────┼─────────┘
           ↓
        Analyzer
           ↓
        Critic
           ↓
        Writer
           ↓
      Final Report
```

### 拓扑 B：Debate（开放性问题）

适合争议性观点分析、策略选择等非标准答案问题：

```
          Planner
             ↓
       Debate Questions
             ↓
 ┌───────────┼───────────┐
 ↓           ↓           ↓
Pro Agent   Con Agent   Neutral Agent
 ↓           ↓           ↓
Evidence    Evidence    Evidence
 └───────────┼───────────┘
             ↓
          Critic
             ↓
        Synthesizer
             ↓
          Writer
             ↓
      Final Research Memo
```

---

## 技术栈

| 技术 | 用途 |
|------|------|
| Python 3.11+ | 主开发语言 |
| FastAPI | API 服务与 OpenAPI 文档 |
| LangGraph + asyncio | Agent 流程编排与并行执行 |
| Pydantic v2 | Schema 校验与数据建模 |
| Redis | 缓存、任务状态持久化、限流 |
| tenacity | 重试、退避、熔断恢复 |
| httpx | 异步 HTTP 调用 |
| Vue 3 + TailwindCSS | 前端界面 |

---

## Agent 角色

| Agent | 职责 | 模型需求 |
|-------|------|----------|
| **Planner** | 研究任务理解与拆解 | 强推理 |
| **Searcher** | 查询改写与网页检索 | 联网搜索 |
| **Reader** | 长文本阅读与摘要抽取 | 高性价比长文本 |
| **Analyzer** | 跨信源分析与矛盾识别 | 长文本分析 |
| **Critic** | 批判性审稿与事实校验 | 强推理 |
| **Writer** | 结构化研究报告生成 | 强写作 |
| **Validator** | 输出 Schema 校验与质量把关 | 轻量校验 |

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- Redis（可选，不启动则使用内存缓存回退）

### 1. 后端启动

```bash
cd deep_research_system

# 创建虚拟环境
python -m venv venv
source venv/bin/activate   # macOS/Linux

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，至少填写一个模型的 API Key

# 启动服务
python main.py
```

### 2. 前端启动

```bash
cd deep_research_system/frontend

npm install
npm run dev
```

访问 `http://localhost:3000` 即可使用。

### 3. 快速验证

```bash
# 健康检查
curl http://localhost:8000/api/health

# 发起研究任务
curl -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{"query": "2025年AI Agent市场趋势分析", "task_type": "industry_report", "depth": "quick"}'
```

---

## 项目结构

```
deep_research_system/
├── main.py                  # 后端入口
├── .env                     # 环境变量
├── config/                  # YAML 配置（模型、Agent、拓扑）
├── prompts/                 # Jinja2 提示词模板（版本化管理）
│   ├── planner/             # 规划 Agent 提示词
│   ├── searcher/            # 搜索 Agent 提示词
│   ├── reader/              # 阅读 Agent 提示词
│   ├── analyzer/            # 分析 Agent 提示词
│   ├── critic/              # 审稿 Agent 提示词
│   ├── writer/              # 写作 Agent 提示词
│   ├── validator/           # 校验 Agent 提示词
│   └── debate/              # 辩论 Agent 提示词
├── app/
│   ├── agents/              # Agent 实现（Planner/Searcher/Reader/...）
│   ├── topology/            # 拓扑编排（Hierarchical / Debate）
│   ├── model_pool/          # 模型路由、Key 池、熔断器
│   ├── schemas/             # Pydantic 数据模型
│   ├── services/            # 业务服务（搜索/缓存/任务状态）
│   └── core/                # 配置/日志/中间件/安全
├── frontend/                # Vue 3 前端
├── tests/                   # 测试用例
└── output/reports/          # 生成的报告
```

---

## 模型配置

系统支持异构模型接入，通过 `config/models.yaml` 配置。初版建议接入 3 类模型：

| 模型类型 | 推荐用途 | 示例 |
|----------|----------|------|
| 联网搜索模型 | Searcher | DeepSeek-Chat |
| 高性价比长文本模型 | Reader / Analyzer | GLM-4-Long |
| 强推理/写作模型 | Planner / Critic / Writer | DeepSeek-Reasoner |

所有模型均通过 API 调用，兼容 OpenAI 接口标准，支持国产模型 API。

---

## License

MIT
