# Deep Research System

基于 FastAPI + LangGraph 的多 Agent 智能检索分析系统

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.0%2B-orange)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📖 项目概述

Deep Research System 是一个基于多 Agent 架构的智能检索分析系统，旨在通过 AI 代理的协同工作，实现深度信息检索、智能分析和结构化报告生成。系统采用模块化设计，支持可扩展的 Agent 工作流，适用于学术研究、市场分析、技术调研等多种场景。

### ✨ 核心特性

- **🤖 多 Agent 协同**: 基于 LangGraph 的 Agent 编排系统，支持复杂的多步骤工作流
- **🔍 智能检索**: 集成多种搜索源（Google、学术论文、代码库等）
- **📊 深度分析**: AI 驱动的信息分析和结构化处理
- **🔄 运行时纠偏**: 基于 Pydantic Schema 的自动校验和纠错
- **🔒 安全脱敏**: 敏感信息自动检测和脱敏处理
- **⚡ 高性能**: 异步架构、缓存优化、并行处理
- **📈 可扩展**: 模块化设计，支持自定义 Agent 和插件

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    API 层 (FastAPI)                     │
│       接口路由、参数校验、统一响应、限流控制            │
├─────────────────────────────────────────────────────────┤
│                 Agent 编排层 (LangGraph)                 │
│       状态管理、节点调度、并行执行、条件分支            │
├─────────────────────────────────────────────────────────┤
│                     服务层 (Service)                     │
│       LLM调用、搜索服务、API池、脱敏服务、缓存          │
├─────────────────────────────────────────────────────────┤
│                     数据层 (Redis)                      │
│       任务状态持久化、缓存管理、限流计数、会话存储      │
└─────────────────────────────────────────────────────────┘
```

### 核心 Agent 节点

1. **规划器 (Planner)**: 解析用户需求，制定研究计划
2. **搜索器 (Searcher)**: 多源信息检索，获取相关数据
3. **阅读器 (Reader)**: 内容解析和摘要生成
4. **分析器 (Analyzer)**: 深度分析和模式识别
5. **评审员 (Critic)**: 质量评估和反馈循环
6. **编写器 (Writer)**: 结构化报告生成

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Redis 7.0+
- 至少 8GB RAM
- 网络连接（用于 API 调用）

### 安装步骤

1. **克隆项目**

```bash
git clone https://github.com/your-username/deep-research-system.git
cd deep-research-system
```

2. **创建虚拟环境**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
```

3. **安装依赖**

```bash
pip install -e ".[dev]"  # 安装开发环境依赖
```

4. **配置环境变量**

```bash
cp .env.example .env
# 编辑 .env 文件，填入您的 API 密钥和其他配置
```

5. **启动 Redis**

```bash
docker run -d -p 6379:6379 --name deep-research-redis redis:7-alpine
```

6. **启动应用**

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

7. **访问应用**

- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health
- Redoc 文档: http://localhost:8000/redoc

## 📁 项目结构

```
deep_research_system/
├── app/                           # 应用核心代码
│   ├── api/                       # API 路由层
│   │   └── v1/                    # API v1 版本
│   ├── agents/                    # Agent 定义
│   │   ├── planner.py            # 规划器 Agent
│   │   ├── searcher.py           # 搜索器 Agent
│   │   ├── reader.py             # 阅读器 Agent
│   │   ├── analyzer.py           # 分析器 Agent
│   │   ├── critic.py             # 评审员 Agent
│   │   └── writer.py             # 编写器 Agent
│   ├── core/                     # 核心配置
│   │   ├── config.py            # 应用配置
│   │   ├── constants.py         # 常量定义
│   │   └── logger.py            # 日志配置
│   ├── model_pool/               # 模型池管理
│   │   ├── llm_pool.py          # LLM 模型池
│   │   └── embedding_pool.py    # 嵌入模型池
│   ├── prompts/                  # 系统提示词
│   │   ├── system_prompts.py    # 系统级提示词
│   │   └── task_prompts.py      # 任务级提示词
│   ├── schemas/                  # 数据模型
│   │   ├── request.py           # 请求模型
│   │   ├── response.py          # 响应模型
│   │   └── agent.py             # Agent 状态模型
│   ├── services/                 # 业务服务
│   │   ├── llm_service.py       # LLM 服务
│   │   ├── search_service.py    # 搜索服务
│   │   ├── cache_service.py     # 缓存服务
│   │   └── desensitize_service.py # 脱敏服务
│   ├── topology/                 # 工作流拓扑
│   │   ├── research_graph.py    # 研究工作流图
│   │   └── utils.py             # 图工具函数
│   └── utils/                    # 工具函数
│       ├── validation.py        # 验证工具
│       ├── formatting.py        # 格式化工具
│       └── security.py          # 安全工具
├── config/                       # 配置文件
│   ├── settings.yaml            # 应用设置
│   └── prompts.yaml             # 提示词配置
├── prompts/                      # 提示词模板
│   ├── planner/                 # 规划器提示词
│   ├── searcher/                # 搜索器提示词
│   ├── reader/                  # 阅读器提示词
│   ├── analyzer/                # 分析器提示词
│   ├── critic/                  # 评审员提示词
│   └── writer/                  # 编写器提示词
├── tests/                        # 测试用例
│   ├── unit/                    # 单元测试
│   ├── integration/             # 集成测试
│   └── fixtures/                # 测试固件
├── scripts/                      # 工具脚本
│   ├── setup.py                 # 安装脚本
│   ├── deploy.py                # 部署脚本
│   └── monitor.py               # 监控脚本
├── main.py                       # 应用入口
├── pyproject.toml               # 项目配置
├── .env.example                 # 环境变量示例
└── README.md                    # 项目说明
```

## 🛠️ 开发指南

### 代码规范

- **代码格式化**: 使用 Black 进行代码格式化
- **代码检查**: 使用 Ruff 进行代码检查
- **类型检查**: 使用 MyPy 进行类型检查
- **提交前检查**: 使用 pre-commit hooks

### 开发命令

```bash
# 代码格式化
black .

# 代码检查
ruff check .

# 类型检查
mypy .

# 运行测试
pytest

# 运行特定测试
pytest tests/unit/test_agents.py -v

# 测试覆盖率
pytest --cov=app --cov-report=html

# 启动开发服务器
uvicorn main:app --reload

# 安装开发环境
pip install -e ".[dev]"
```

### 添加新的 Agent

1. 在 `app/agents/` 目录下创建新的 Agent 文件
2. 实现 Agent 的核心逻辑
3. 在 `app/schemas/agent.py` 中定义 Agent 状态模型
4. 在 `app/topology/research_graph.py` 中集成到工作流
5. 编写测试用例

## 📚 API 文档

### 主要端点

#### POST `/api/v1/research/start`
启动一个新的研究任务

**请求体**:
```json
{
  "query": "研究人工智能在医疗诊断中的应用",
  "max_depth": 3,
  "language": "zh",
  "format": "markdown"
}
```

**响应**:
```json
{
  "task_id": "uuid-string",
  "status": "pending",
  "message": "研究任务已开始"
}
```

#### GET `/api/v1/research/{task_id}/status`
获取研究任务状态

#### GET `/api/v1/research/{task_id}/result`
获取研究结果

#### POST `/api/v1/research/{task_id}/cancel`
取消研究任务

### WebSocket 端点

#### `/ws/research/{task_id}`
实时获取研究进度更新

## 🔧 配置说明

### 环境变量

详见 `.env.example` 文件，主要配置包括：

- **AI 模型**: OpenAI, Anthropic, Google Gemini 等
- **搜索服务**: Serper, Tavily, Google Custom Search 等
- **数据库**: Redis 连接配置
- **安全**: JWT 密钥、API 限流
- **性能**: 并发限制、缓存配置

### 配置文件

- `config/settings.yaml`: 应用级设置
- `config/prompts.yaml`: 提示词配置

## 🧪 测试

### 测试结构

```bash
tests/
├── unit/           # 单元测试
├── integration/    # 集成测试
├── e2e/           # 端到端测试
└── fixtures/      # 测试固件
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 生成测试覆盖率报告
pytest --cov=app --cov-report=html
```

## 🚢 部署

### 本地部署

```bash
# 使用 Docker Compose
docker-compose up -d

# 手动部署
./scripts/deploy.sh
```

### 云部署

支持部署到:
- AWS ECS/EKS
- Google Cloud Run
- Azure Container Instances
- 自托管服务器

### 监控和日志

- **日志**: 结构化日志输出到 stdout
- **监控**: Prometheus 指标收集
- **告警**: Sentry 错误监控
- **性能**: APM 工具集成

## 🤝 贡献指南

欢迎贡献代码！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何参与项目开发。

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代、快速的 Web 框架
- [LangGraph](https://langchain-ai.github.io/langgraph/) - 多 Agent 编排框架
- [LangChain](https://www.langchain.com/) - LLM 应用开发框架
- [Pydantic](https://docs.pydantic.dev/) - 数据验证和设置管理

## 📞 支持

- 问题反馈: [GitHub Issues](https://github.com/your-username/deep-research-system/issues)
- 文档: [项目 Wiki](https://github.com/your-username/deep-research-system/wiki)
- 讨论: [GitHub Discussions](https://github.com/your-username/deep-research-system/discussions)

---

<p align="center">
  Made with ❤️ by the Deep Research System Team
</p>