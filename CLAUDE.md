# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 项目概述
这是一个 **FastAPI + LangGraph 多Agent智能检索分析系统** 学习项目，目标是打造具备后端工程化、多Agent并行、运行时纠偏、安全脱敏等特性的可演示项目，用于简历包装和求职。

**技术栈**：Python 3.11+ + FastAPI + LangGraph + Redis + Tenacity + Microsoft Presidio

---

## 项目状态
⚠️ **当前阶段：项目规划完成，待开发**
- 需求文档已完成并对齐工业界架构
- 详细开发计划已制定（12天分阶段）
- 尚未创建实际代码文件

---

## 核心架构
```
┌─────────────────────────────────────────┐
│        API 层 (FastAPI)                 │
│  接口路由、参数校验、统一响应、限流      │
├─────────────────────────────────────────┤
│        Agent 编排层 (LangGraph)          │
│  状态管理、节点调度、并行执行、条件边    │
├─────────────────────────────────────────┤
│        服务层 (Service)                  │
│  LLM调用、搜索服务、API池、脱敏服务      │
├─────────────────────────────────────────┤
│        数据层 (Redis)                    │
│  缓存、任务状态持久化、限流计数          │
└─────────────────────────────────────────┘
```

### 核心Agent节点
1. **scheduler_node** - 调度Agent：解析问题，拆分子任务
2. **retrieval_node** - 检索Agent：调用Serper搜索
3. **analysis_node** - 分析Agent：深度分析搜索结果（并行执行）
4. **validate_node** - 校验Agent：Pydantic Schema校验（运行时纠偏）
5. **summary_node** - 汇总Agent：合并输出+脱敏

---

## 项目文档
| 文档 | 用途 |
|------|------|
| `需求.md` | 原始需求+架构调整说明+分阶段计划 |
| `详细开发计划.md` | 逐天任务清单、依赖库列表、验收标准 |

---

## 常用命令（开发阶段）

### 环境设置
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 安装依赖（后续会生成requirements.txt）
pip install fastapi uvicorn redis langgraph langchain-openai tenacity
```

### 开发服务
```bash
# 启动开发服务器（热重载）
uvicorn main:app --reload --port 8000

# 启动Redis（Docker方式）
docker run -d -p 6379:6379 --name agent-redis redis:7-alpine
```

### 代码质量
```bash
# 代码格式化
black .

# Lint检查
ruff check .

# 类型检查
mypy .
```

### 测试
```bash
# 运行所有测试
pytest

# 运行单个测试文件
pytest tests/test_api.py -v

# 运行单个测试用例
pytest tests/test_api.py::test_chat_endpoint -v
```

---

## 开发指引
1. **按阶段开发**：严格按照`详细开发计划.md`的Day1-Day12顺序进行
2. **技术栈统一**：全Python，不引入Java/跨语言组件
3. **安全优先**：API Key等敏感信息必须放在`.env`，禁止硬编码
4. **Git提交**：每天完成任务后提交，commit message清晰描述改动

---

## 关键文件位置（未来将创建）
```
multi_agent_ir/
├── app/
│   ├── api/           # FastAPI路由
│   ├── core/          # 配置、常量
│   ├── schemas/       # Pydantic模型
│   ├── services/      # 业务服务（LLM、搜索、API池）
│   ├── agents/        # LangGraph节点定义
│   └── utils/         # 工具类（脱敏、日志、签名）
├── config/            # 配置文件
├── tests/             # 测试用例
├── main.py            # 入口文件
├── .env               # 环境变量（不提交Git）
└── requirements.txt   # 依赖清单
```
