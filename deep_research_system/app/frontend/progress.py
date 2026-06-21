"""Progress tracking for frontend.

Maps LangGraph node events to progress percentages and stage labels.
Supports both hierarchical and debate topologies.
"""

from __future__ import annotations

from typing import TypedDict

from app.domain.enums import ResearchStrategy


class ProgressInfo(TypedDict):
    """Progress information for frontend."""
    progress: int
    stage: str
    stage_label: str
    topology: str


class ProgressTracker:
    """Tracks progress for research runs.

    Maps node names to progress percentages and stage labels.
    """

    # Progress mapping for hierarchical topology
    HIERARCHICAL_PROGRESS = {
        "prepare_research": 5,
        "dispatch_research_wave": 10,
        "research_branch": 20,
        "join_research": 30,
        "build_analysis": 40,
        "critique": 50,
        "generate_followups": 55,
        "write_report": 70,
        "validate_report": 85,
        "repair_report": 90,
        "finalize_hierarchical": 100,
        "quality_gate_failed": 100,
    }

    # Progress mapping for debate topology
    DEBATE_PROGRESS = {
        "generate_hypotheses": 5,
        "dispatch_debate_branches": 10,
        "debate_branch": 25,
        "join_debate": 35,
        "cross_examine": 45,
        "synthesize": 60,
        "write_report": 75,
        "validate_report": 85,
        "repair_report": 90,
        "finalize_debate": 100,
        "quality_gate_failed": 100,
    }

    # Stage labels (Chinese)
    STAGE_LABELS = {
        # Hierarchical
        "prepare_research": "准备研究",
        "dispatch_research_wave": "分发研究任务",
        "research_branch": "执行研究分支",
        "join_research": "汇总研究结果",
        "build_analysis": "构建分析",
        "critique": "审稿",
        "generate_followups": "生成补充问题",
        "write_report": "撰写报告",
        "validate_report": "验证报告",
        "repair_report": "修复报告",
        "finalize_hierarchical": "完成",
        "quality_gate_failed": "质量检查失败",
        # Debate
        "generate_hypotheses": "生成假设",
        "dispatch_debate_branches": "分发辩论分支",
        "debate_branch": "执行辩论分支",
        "join_debate": "汇总辩论结果",
        "cross_examine": "交叉检验",
        "synthesize": "综合观点",
        "finalize_debate": "完成",
        # Common
        "running": "运行中",
        "completed": "已完成",
        "failed": "失败",
        "failed_quality_gate": "质量检查失败",
        "cancelled": "已取消",
    }

    def __init__(self, topology: str = ResearchStrategy.HIERARCHICAL.value) -> None:
        self._topology = topology
        self._progress_map = (
            self.DEBATE_PROGRESS if topology == ResearchStrategy.DEBATE.value
            else self.HIERARCHICAL_PROGRESS
        )

    def get_progress(self, node: str | None) -> int:
        """Get progress percentage for a node."""
        if not node:
            return 0
        return self._progress_map.get(node, 0)

    def get_stage_label(self, stage: str | None) -> str:
        """Get human-readable stage label."""
        if not stage:
            return "初始化"

        # Check direct mapping
        if stage in self.STAGE_LABELS:
            return self.STAGE_LABELS[stage]

        # Dynamic debate branches: support-0, oppose-1, etc.
        if stage.startswith(("support-", "oppose-", "alternative-")):
            position, idx = stage.rsplit("-", 1)
            position_label = {
                "support": "支持",
                "oppose": "反对",
                "alternative": "替代",
            }.get(position, position)
            return f"辩论-{position_label} #{idx}"

        # Subtask agents: searcher_sq_1, etc.
        if "_sq_" in stage:
            parts = stage.split("_sq_")
            base = self.STAGE_LABELS.get(parts[0], parts[0])
            return f"{base} #{parts[1]}"

        # Repair writer
        if stage == "repair_writer" or stage.startswith("repair_writer_"):
            num = stage.split("_")[-1] if stage != "repair_writer" else None
            return f"修复写作中 #{num}" if num else "修复写作中"

        return stage

    def get_progress_info(self, node: str | None, status: str | None = None) -> ProgressInfo:
        """Get complete progress info."""
        progress = self.get_progress(node)

        # Override for terminal states
        if status in ("completed", "failed", "failed_quality_gate", "cancelled"):
            progress = 100 if status == "completed" else progress

        return {
            "progress": progress,
            "stage": node or "init",
            "stage_label": self.get_stage_label(node or "init"),
            "topology": self._topology,
        }

    @classmethod
    def for_topology(cls, topology: str) -> "ProgressTracker":
        """Create a progress tracker for a specific topology."""
        return cls(topology)
