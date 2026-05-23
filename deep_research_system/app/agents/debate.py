from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base import BaseAgent
from app.schemas.state import ResearchState
from app.schemas.task import TaskRequirement

logger = logging.getLogger(__name__)


class DebateAgent(BaseAgent):
    name = "debate"
    prompt_template_name = "searcher/v2_query_expansion.zh.j2"

    def __init__(self, branch: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.branch = branch
        self.name = branch

    def requirement(self, state: ResearchState) -> TaskRequirement:
        return TaskRequirement(
            required_capabilities=["reasoning", "web_search_native"],
            preferred_cost_tier="mid",
            complexity="medium",
        )

    def _build_prompt(self, state: ResearchState) -> str:
        branch_instructions = {
            "pro": "从支持方的角度研究这个问题，收集支持性证据和论点。",
            "con": "从反对方的角度研究这个问题，收集反对性证据和论点。",
            "neutral": "从中立的角度研究这个问题，整理事实边界、适用条件和不确定性。",
        }
        instruction = branch_instructions.get(self.branch, "")
        return f"""你是一个{self.branch.upper()}方研究员。

## 研究问题
{state.task.user_query}

## 你的任务
{instruction}

## 输出格式
请以 JSON 格式输出：
```json
{{
  "branch": "{self.branch}",
  "position": "你的立场概述",
  "evidence": [
    {{
      "claim": "具体声明",
      "source_url": "来源URL",
      "quote_or_summary": "引用或摘要",
      "confidence": 0.8
    }}
  ],
  "arguments": ["论点1", "论点2"]
}}
```"""

    def _parse_output(self, content: str) -> dict:
        result = super()._parse_output(content)
        result.setdefault("branch", self.branch)
        return result


class SynthesizerAgent(BaseAgent):
    name = "synthesizer"
    prompt_template_name = "analyzer/v1_cross_source.zh.j2"

    def requirement(self, state: ResearchState) -> TaskRequirement:
        return TaskRequirement(
            required_capabilities=["strong_reasoning", "synthesis"],
            preferred_cost_tier="high",
            complexity="hard",
        )

    def _build_prompt(self, state: ResearchState) -> str:
        debate = state.debate_results
        return f"""你是一个综合分析师。你的任务是综合三方辩论结果，找出关键分歧并给出条件化结论。

## 研究问题
{state.task.user_query}

## 支持方观点
{json.dumps(debate.get('pro', {}), ensure_ascii=False, indent=2)}

## 反对方观点
{json.dumps(debate.get('con', {}), ensure_ascii=False, indent=2)}

## 中立方观点
{json.dumps(debate.get('neutral', {}), ensure_ascii=False, indent=2)}

## 输出格式
```json
{{
  "key_disagreements": ["分歧点1"],
  "conditional_conclusions": ["在X条件下，Y成立"],
  "consensus_points": ["共识1"],
  "open_questions": ["未解决问题1"]
}}
```"""
