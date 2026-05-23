"""Demo script for Deep Research System with detailed output."""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.research_service import ResearchService

# 配置日志 - 显示 Agent 执行过程
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 报告输出目录
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "reports"


def save_report(report: dict, task_id: str, task_type: str) -> Path:
    """保存报告到指定目录."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{task_type}_{task_id}_{timestamp}.md"
    filepath = OUTPUT_DIR / filename
    
    # 构建 Markdown 内容
    content = f"""# {report.get('title', 'Untitled Report')}

**Task ID:** {task_id}  
**Task Type:** {task_type}  
**Generated at:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

"""
    
    # 添加执行摘要
    if 'executive_summary' in report:
        content += f"## 执行摘要\n\n{report['executive_summary']}\n\n"
    
    # 添加各个章节
    sections = report.get('sections', [])
    for i, section in enumerate(sections, 1):
        title = section.get('title', f'Section {i}')
        content_text = section.get('content', '')
        content += f"## {i}. {title}\n\n{content_text}\n\n"
    
    # 添加结论
    if 'conclusion' in report:
        content += f"## 结论\n\n{report['conclusion']}\n\n"
    
    # 添加参考来源
    if 'sources' in report and report['sources']:
        content += "## 参考来源\n\n"
        for j, source in enumerate(report['sources'], 1):
            content += f"{j}. {source}\n"
        content += "\n"
    
    # 保存文件
    filepath.write_text(content, encoding='utf-8')
    return filepath


def print_report_content(report: dict) -> None:
    """在终端打印报告内容."""
    print("\n" + "=" * 80)
    print("📄 报告内容")
    print("=" * 80)
    
    title = report.get('title', 'Untitled')
    print(f"\n【标题】{title}\n")
    
    # 执行摘要
    if 'executive_summary' in report:
        print("-" * 80)
        print("【执行摘要】")
        print("-" * 80)
        print(report['executive_summary'])
        print()
    
    # 各章节
    sections = report.get('sections', [])
    if sections:
        print("-" * 80)
        print(f"【正文 - 共 {len(sections)} 个章节】")
        print("-" * 80)
        for i, section in enumerate(sections, 1):
            section_title = section.get('title', f'章节 {i}')
            section_content = section.get('content', '')
            print(f"\n### {i}. {section_title}\n")
            print(section_content[:1000] if len(section_content) > 1000 else section_content)
            if len(section_content) > 1000:
                print(f"\n... (章节内容已截断，完整内容请查看保存的文件)")
            print()
    
    # 结论
    if 'conclusion' in report:
        print("-" * 80)
        print("【结论】")
        print("-" * 80)
        print(report['conclusion'])
        print()
    
    # 参考来源
    sources = report.get('sources', [])
    if sources:
        print("-" * 80)
        print(f"【参考来源 - 共 {len(sources)} 个】")
        print("-" * 80)
        for j, source in enumerate(sources, 1):
            print(f"{j}. {source}")
        print()
    
    print("=" * 80)


def print_audit_trail(audit_trail: list) -> None:
    """打印 Agent 执行审计日志."""
    print("\n" + "=" * 80)
    print("🔍 Agent 执行过程")
    print("=" * 80)
    
    for i, entry in enumerate(audit_trail, 1):
        agent = entry.get('agent', 'unknown')
        model = entry.get('model', 'unknown')
        prompt_version = entry.get('prompt_version', 'N/A')
        token_in = entry.get('token_in', 0)
        token_out = entry.get('token_out', 0)
        cost = entry.get('cost', 0)
        latency = entry.get('latency_ms', 0)
        
        print(f"\n  Step {i}: {agent.upper()}")
        print(f"    - Model: {model}")
        print(f"    - Prompt Version: {prompt_version}")
        print(f"    - Tokens: {token_in} in / {token_out} out")
        print(f"    - Cost: ${cost:.6f}")
        print(f"    - Latency: {latency:.0f}ms")
    
    print("\n" + "=" * 80)


async def demo_industry_report() -> None:
    print("\n" + "=" * 80)
    print("🏭 Demo 1: 行业报告 (Hierarchical Topology)")
    print("=" * 80)

    service = ResearchService()
    await service.initialize()

    result = await service.create_task_sync({
        "user_query": "请生成一份 2026 年中国 AI Agent 行业发展报告",
        "task_type": "industry_report",
        "depth": "standard",
        "budget_level": "medium",
    })

    print(f"\n📋 任务信息:")
    print(f"   Task ID: {result.get('task_id')}")
    print(f"   Status: {result.get('status')}")
    print(f"   Topology: {result.get('selected_topology')}")

    task_result = result.get("result", {})
    if task_result:
        report = task_result.get("report", {})
        metrics = task_result.get("metrics", {})
        audit_trail = task_result.get("audit_trail", [])
        
        # 打印基本指标
        print(f"\n📊 执行指标:")
        print(f"   Title: {report.get('title', 'N/A')}")
        print(f"   Sections: {len(report.get('sections', []))}")
        print(f"   Cost: ${metrics.get('cost_so_far', 0):.4f}")
        print(f"   Latency: {metrics.get('latency_ms', 0):.0f}ms")
        print(f"   Model Calls: {json.dumps(metrics.get('model_usage', {}), indent=4)}")
        
        # 打印 Agent 执行过程
        if audit_trail:
            print_audit_trail(audit_trail)
        
        # 打印报告内容
        if report:
            print_report_content(report)
            
            # 保存报告
            task_id = result.get('task_id', 'unknown')
            filepath = save_report(report, task_id, "industry_report")
            print(f"\n💾 报告已保存到: {filepath}")
    
    print()


async def demo_open_question() -> None:
    print("\n" + "=" * 80)
    print("💬 Demo 2: 开放性问题 (Debate Topology)")
    print("=" * 80)

    service = ResearchService()
    await service.initialize()

    result = await service.create_task_sync({
        "user_query": "未来两年企业是否应该优先投入多 Agent 系统，而不是单 Agent 工具链？",
        "task_type": "open_question",
        "depth": "standard",
        "budget_level": "high",
    })

    print(f"\n📋 任务信息:")
    print(f"   Task ID: {result.get('task_id')}")
    print(f"   Status: {result.get('status')}")
    print(f"   Topology: {result.get('selected_topology')}")

    task_result = result.get("result", {})
    if task_result:
        report = task_result.get("report", {})
        metrics = task_result.get("metrics", {})
        audit_trail = task_result.get("audit_trail", [])
        
        # 打印基本指标
        print(f"\n📊 执行指标:")
        print(f"   Title: {report.get('title', 'N/A')}")
        print(f"   Sections: {len(report.get('sections', []))}")
        print(f"   Cost: ${metrics.get('cost_so_far', 0):.4f}")
        print(f"   Latency: {metrics.get('latency_ms', 0):.0f}ms")
        print(f"   Model Calls: {json.dumps(metrics.get('model_usage', {}), indent=4)}")
        
        # 打印 Agent 执行过程
        if audit_trail:
            print_audit_trail(audit_trail)
        
        # 打印报告内容
        if report:
            print_report_content(report)
            
            # 保存报告
            task_id = result.get('task_id', 'unknown')
            filepath = save_report(report, task_id, "open_question")
            print(f"\n💾 报告已保存到: {filepath}")
    
    print()


async def main() -> None:
    print("\n" + "🚀" * 40)
    print("Deep Research System - Enhanced Demo")
    print("🚀" * 40)
    print(f"\n📁 报告将保存到: {OUTPUT_DIR}")
    print()

    if "--industry" in sys.argv or len(sys.argv) == 1:
        await demo_industry_report()
    if "--debate" in sys.argv or len(sys.argv) == 1:
        await demo_open_question()

    print("\n" + "✅" * 40)
    print("所有任务已完成！")
    print("✅" * 40)


if __name__ == "__main__":
    asyncio.run(main())
