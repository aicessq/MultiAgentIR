from __future__ import annotations

import json
import logging
from typing import Any, Callable

from pydantic import BaseModel

from app.model_pool.client import LLMClient, LLMCallResult, StreamResult
from app.model_pool.key_pool import APIKeyPool
from app.model_pool.router import FallbackRouter
from app.prompts.renderer import get_prompt_loader
from app.schemas.state import ResearchState
from app.schemas.task import TaskRequirement

logger = logging.getLogger(__name__)

# 默认费率（每 1K tokens，美元），可通过 config/app.yaml 覆盖
DEFAULT_INPUT_COST = 0.002
DEFAULT_OUTPUT_COST = 0.006


class BaseAgent:
    name: str = "base"
    prompt_template_name: str = ""

    def __init__(self, router: FallbackRouter, llm_client: LLMClient, key_pool: APIKeyPool) -> None:
        self.router = router
        self.llm_client = llm_client
        self.key_pool = key_pool
        self.prompt_loader = get_prompt_loader()

    def requirement(self, state: ResearchState) -> TaskRequirement:
        return TaskRequirement()

    @staticmethod
    def _emit(on_event: Callable | None, event: dict) -> None:
        if on_event is None:
            return
        try:
            on_event(event)
        except Exception:
            pass

    def _summarize_output(self, parsed: dict) -> str:
        if self.name == "planner":
            sqs = parsed.get("sub_questions", [])
            return f"规划完成: {len(sqs)} 个子问题"
        if self.name == "searcher":
            sources = parsed.get("sources", [])
            return f"搜索完成: {len(sources)} 条来源"
        if self.name == "reader":
            findings = parsed.get("key_findings", [])
            evidence = parsed.get("evidence", [])
            return f"阅读完成: {len(findings)} 条发现, {len(evidence)} 条证据"
        if self.name == "analyzer":
            return "分析完成"
        if self.name == "critic":
            issues = parsed.get("issues", [])
            return f"审稿完成: {len(issues)} 个问题"
        if self.name == "writer":
            title = parsed.get("title", "")
            return f"写作完成: {title}" if title else "写作完成"
        if self.name == "validator":
            valid = parsed.get("valid", False)
            return "验证通过" if valid else "验证发现问题"
        if self.name in ("pro", "con", "neutral"):
            return f"{self.name.upper()} 论述完成"
        if self.name == "synthesizer":
            return "综合分析完成"
        return "完成"

    async def run(self, state: ResearchState, on_event: Callable | None = None) -> dict:
        requirement = self.requirement(state)
        model = await self.router.select_model(requirement)
        if not model:
            raise RuntimeError(f"No model available for {self.name}")

        self._emit(on_event, {
            "type": "agent_model_selected",
            "agent": self.name,
            "model": model.name,
            "message": f"已选择模型: {model.name}",
        })

        api_key = self.key_pool.get_api_key(model.name) or ""
        prompt = self._build_prompt(state)
        system_prompt = self._system_prompt()

        self._emit(on_event, {
            "type": "agent_thinking",
            "agent": self.name,
            "message": f"正在思考... (prompt {len(prompt)} chars)",
        })

        # Stream LLM response token by token
        collector = StreamResult()
        content_parts: list[str] = []
        async for token in self.llm_client.stream(model, prompt, system_prompt, api_key, result_collector=collector):
            content_parts.append(token)
            self._emit(on_event, {
                "type": "agent_stream_token",
                "agent": self.name,
                "token": token,
            })

        full_content = "".join(content_parts)
        result = LLMCallResult(
            content=full_content,
            prompt_tokens=collector.prompt_tokens,
            completion_tokens=collector.completion_tokens,
            latency_ms=collector.latency_ms,
            model_name=model.name,
        )

        self._emit(on_event, {
            "type": "agent_thinking",
            "agent": self.name,
            "message": f"模型响应完成 ({result.latency_ms:.0f}ms, {result.completion_tokens} tokens)",
            "latency_ms": result.latency_ms,
            "tokens": result.completion_tokens,
        })

        state.add_audit(
            agent=self.name,
            model=model.name,
            prompt_version=self.prompt_loader.get_version(self.prompt_template_name),
            token_in=result.prompt_tokens,
            token_out=result.completion_tokens,
            cost=self._estimate_cost(model.name, result),
            latency_ms=result.latency_ms,
        )

        parsed = self._parse_output(result.content)

        self._emit(on_event, {
            "type": "agent_output",
            "agent": self.name,
            "output": parsed,
            "message": self._summarize_output(parsed),
        })

        return parsed

    def _build_prompt(self, state: ResearchState) -> str:
        return self.prompt_loader.render(
            self.prompt_template_name,
            **self._prompt_context(state),
        )

    def _prompt_context(self, state: ResearchState) -> dict[str, Any]:
        return {"user_query": state.task.user_query, "task_type": state.task.task_type}

    def _system_prompt(self) -> str:
        return ""

    def _parse_output(self, content: str) -> dict:
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
        return {"raw_content": content}

    def _estimate_cost(self, model_name: str, result: LLMCallResult) -> float:
        from app.core.config import get_config
        cost_cfg = get_config().app.get("cost_estimates", {})
        model_costs = cost_cfg.get(model_name, {})
        inp = model_costs.get("input_per_1k", DEFAULT_INPUT_COST)
        out = model_costs.get("output_per_1k", DEFAULT_OUTPUT_COST)
        return (result.prompt_tokens * inp + result.completion_tokens * out) / 1000
