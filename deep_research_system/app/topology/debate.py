from __future__ import annotations

import asyncio
import logging

from app.agents.critic import CriticAgent
from app.agents.debate import DebateAgent, SynthesizerAgent
from app.agents.planner import PlannerAgent
from app.agents.validator import ValidatorAgent
from app.agents.writer import WriterAgent
from app.model_pool.client import LLMClient
from app.model_pool.key_pool import APIKeyPool
from app.model_pool.registry import ModelRegistry
from app.model_pool.router import FallbackRouter
from app.schemas.state import ResearchState
from app.topology.base import BaseTopology, EventCallback

logger = logging.getLogger(__name__)


class DebateTopology(BaseTopology):
    name = "debate"

    def __init__(self) -> None:
        self._registry = ModelRegistry()
        self._key_pool = APIKeyPool()
        self._router = FallbackRouter(self._registry, self._key_pool)
        self._llm_client = LLMClient()

        self.planner = PlannerAgent(router=self._router, llm_client=self._llm_client, key_pool=self._key_pool)
        self.critic = CriticAgent(router=self._router, llm_client=self._llm_client, key_pool=self._key_pool)
        self.synthesizer = SynthesizerAgent(router=self._router, llm_client=self._llm_client, key_pool=self._key_pool)
        self.writer = WriterAgent(router=self._router, llm_client=self._llm_client, key_pool=self._key_pool)
        self.validator = ValidatorAgent(router=self._router, llm_client=self._llm_client, key_pool=self._key_pool)

    def _create_debate_agents(self, hypotheses: list[str]) -> dict[str, DebateAgent]:
        """Create one DebateAgent per hypothesis."""
        agents = {}
        for i, hypothesis in enumerate(hypotheses):
            branch_id = f"h_{i}"
            agents[branch_id] = DebateAgent(
                hypothesis=hypothesis,
                branch=branch_id,
                router=self._router,
                llm_client=self._llm_client,
                key_pool=self._key_pool,
            )
        return agents

    async def execute(self, state: ResearchState, on_event: EventCallback = None) -> ResearchState:
        # Step 1: Planner
        state.current_stage = "planner"
        state.progress = 10
        self.emit(on_event, {"type": "stage_start", "agent": "planner", "progress": 10})
        logger.info("Stage: Planner (debate)")
        plan_result = await self.planner.run(state, on_event=on_event)
        state.plan = plan_result.get("sub_questions", [])
        self.emit(on_event, {"type": "stage_complete", "agent": "planner", "progress": 20, "output": plan_result})

        # Step 2: Create debate agents from hypotheses
        hypotheses = plan_result.get("hypotheses", [])
        if not hypotheses:
            # Fallback: extract from sub_questions
            hypotheses = [sq.get("question", "") for sq in state.plan[:3]]
        if not hypotheses:
            hypotheses = [state.task.user_query]

        debate_agents = self._create_debate_agents(hypotheses)

        # Step 3: Debate branches (parallel)
        state.current_stage = "debate"
        state.progress = 30
        for branch in debate_agents:
            self.emit(on_event, {"type": "stage_start", "agent": branch, "progress": 30})
        logger.info(f"Stage: Debate branches ({len(debate_agents)} hypotheses)")

        tasks = {
            branch: agent.run(state, on_event=on_event)
            for branch, agent in debate_agents.items()
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for branch, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Debate {branch} failed: {result}")
                state.errors.append({"stage": "debate", "branch": branch, "error": str(result)})
            else:
                state.debate_results[branch] = result
                # Register sources from debate evidence
                for ev in result.get("evidence", []):
                    url = ev.get("source_url", "")
                    if url and url not in state.source_registry:
                        state.source_registry[url] = {"url": url, "title": "", "source_type": "unknown"}
                self.emit(on_event, {
                    "type": "subtask_complete",
                    "agent": branch,
                    "subtask_id": branch,
                    "message": f"{branch} 假设检验完成",
                    "output": result,
                })
        for branch in debate_agents:
            self.emit(on_event, {"type": "stage_complete", "agent": branch, "progress": 50})

        # Step 4: Critic
        state.current_stage = "critic"
        state.progress = 55
        self.emit(on_event, {"type": "stage_start", "agent": "critic", "progress": 55})
        logger.info("Stage: Critic (cross-examination)")
        critique = await self.critic.run(state, on_event=on_event)
        state.critiques.append(critique)
        self.emit(on_event, {"type": "stage_complete", "agent": "critic", "progress": 65, "output": critique})

        # Step 5: Synthesizer
        state.current_stage = "synthesizer"
        state.progress = 70
        self.emit(on_event, {"type": "stage_start", "agent": "synthesizer", "progress": 70})
        logger.info("Stage: Synthesizer")
        synthesis = await self.synthesizer.run(state, on_event=on_event)
        state.analyses.append(synthesis)
        # Store claim graph from synthesis if available
        if isinstance(synthesis, dict):
            state.claim_graph = synthesis.get("hypothesis_assessment", [])
        self.emit(on_event, {"type": "stage_complete", "agent": "synthesizer", "progress": 75, "output": synthesis})

        # Step 6: Writer
        state.current_stage = "writer"
        state.progress = 85
        self.emit(on_event, {"type": "stage_start", "agent": "writer", "progress": 85})
        logger.info("Stage: Writer (memo)")
        report = await self.writer.run(state, on_event=on_event)
        state.final_report = report
        self.emit(on_event, {"type": "stage_complete", "agent": "writer", "progress": 90, "output": {"title": report.get("title", ""), "executive_summary": report.get("executive_summary", "")}})

        # Step 7: Validator
        state.current_stage = "validator"
        state.progress = 95
        self.emit(on_event, {"type": "stage_start", "agent": "validator", "progress": 95})
        logger.info("Stage: Validator")
        validation = await self.validator.run(state)
        if not validation.get("valid"):
            logger.warning(f"Validation issues: {validation.get('issues')}")
        self.emit(on_event, {"type": "stage_complete", "agent": "validator", "progress": 98, "output": validation})

        state.current_stage = "completed"
        state.progress = 100
        return state
