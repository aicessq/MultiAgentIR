from __future__ import annotations

import asyncio
import logging

from app.agents.analyzer import AnalyzerAgent
from app.agents.base import BaseAgent
from app.agents.critic import CriticAgent
from app.agents.planner import PlannerAgent
from app.agents.reader import ReaderAgent
from app.agents.searcher import SearcherAgent
from app.agents.validator import ValidatorAgent
from app.agents.writer import WriterAgent
from app.model_pool.client import LLMClient
from app.model_pool.key_pool import APIKeyPool
from app.model_pool.registry import ModelRegistry
from app.model_pool.router import FallbackRouter
from app.schemas.state import ResearchState
from app.topology.base import BaseTopology, EventCallback

logger = logging.getLogger(__name__)


class HierarchicalTopology(BaseTopology):
    name = "hierarchical"

    def __init__(self) -> None:
        registry = ModelRegistry()
        key_pool = APIKeyPool()
        router = FallbackRouter(registry, key_pool)
        llm_client = LLMClient()

        self.planner = PlannerAgent(router=router, llm_client=llm_client, key_pool=key_pool)
        self.searcher_cls = lambda: SearcherAgent(router=router, llm_client=llm_client, key_pool=key_pool)
        self.reader_cls = lambda: ReaderAgent(router=router, llm_client=llm_client, key_pool=key_pool)
        self.analyzer = AnalyzerAgent(router=router, llm_client=llm_client, key_pool=key_pool)
        self.critic = CriticAgent(router=router, llm_client=llm_client, key_pool=key_pool)
        self.writer = WriterAgent(router=router, llm_client=llm_client, key_pool=key_pool)
        self.validator = ValidatorAgent(router=router, llm_client=llm_client, key_pool=key_pool)

    async def execute(self, state: ResearchState, on_event: EventCallback = None) -> ResearchState:
        # Step 1: Planner
        state.current_stage = "planner"
        state.progress = 10
        self.emit(on_event, {"type": "stage_start", "agent": "planner", "progress": 10})
        logger.info("Stage: Planner")
        plan_result = await self.planner.run(state, on_event=on_event)
        state.plan = plan_result.get("sub_questions", [])
        if plan_result.get("suggested_topology"):
            state.selected_topology = plan_result["suggested_topology"]
        self.emit(on_event, {"type": "stage_complete", "agent": "planner", "progress": 20, "output": plan_result})

        # Step 2: Searcher (parallel)
        state.current_stage = "searcher"
        state.progress = 25
        self.emit(on_event, {"type": "stage_start", "agent": "searcher", "progress": 25})
        logger.info(f"Stage: Searcher ({len(state.plan)} sub-questions)")
        searcher_tasks = []
        for sq in state.plan:
            searcher = self.searcher_cls()
            sq_state = state.model_copy(deep=True)
            sq_state.plan = [sq]
            searcher_tasks.append(searcher.run(sq_state, on_event=on_event))

        search_results = await asyncio.gather(*searcher_tasks, return_exceptions=True)
        for sq, result in zip(state.plan, search_results):
            if isinstance(result, Exception):
                logger.error(f"Searcher failed for {sq.get('id')}: {result}")
                state.errors.append({"stage": "searcher", "sq_id": sq.get("id"), "error": str(result)})
            else:
                state.sub_results[sq["id"]] = result
                self.emit(on_event, {
                    "type": "subtask_complete",
                    "agent": "searcher",
                    "subtask_id": sq["id"],
                    "message": f"子问题 {sq['id']} 搜索完成",
                    "output": result,
                })
        self.emit(on_event, {"type": "stage_complete", "agent": "searcher", "progress": 35, "output": {"results": list(state.sub_results.keys())}})

        # Step 3: Reader (parallel)
        state.current_stage = "reader"
        state.progress = 45
        self.emit(on_event, {"type": "stage_start", "agent": "reader", "progress": 45})
        logger.info("Stage: Reader")
        reader_tasks = []
        for sq_id, sq_data in state.sub_results.items():
            reader = self.reader_cls()
            sq_state = state.model_copy(deep=True)
            sq_state.sub_results = {sq_id: sq_data}
            reader_tasks.append(reader.run(sq_state, on_event=on_event))

        reader_results = await asyncio.gather(*reader_tasks, return_exceptions=True)
        for (sq_id, _), result in zip(state.sub_results.items(), reader_results):
            if isinstance(result, Exception):
                logger.error(f"Reader failed for {sq_id}: {result}")
            else:
                state.sub_results[sq_id] = {**state.sub_results[sq_id], **result}
                self.emit(on_event, {
                    "type": "subtask_complete",
                    "agent": "reader",
                    "subtask_id": sq_id,
                    "message": f"子问题 {sq_id} 阅读完成",
                    "output": result,
                })
        self.emit(on_event, {"type": "stage_complete", "agent": "reader", "progress": 55, "output": {"sub_results_count": len(state.sub_results)}})

        # Step 4: Analyzer
        state.current_stage = "analyzer"
        state.progress = 60
        self.emit(on_event, {"type": "stage_start", "agent": "analyzer", "progress": 60})
        logger.info("Stage: Analyzer")
        analysis = await self.analyzer.run(state, on_event=on_event)
        state.analyses.append(analysis)
        self.emit(on_event, {"type": "stage_complete", "agent": "analyzer", "progress": 65, "output": analysis})

        # Step 5: Critic
        state.current_stage = "critic"
        state.progress = 75
        self.emit(on_event, {"type": "stage_start", "agent": "critic", "progress": 75})
        logger.info("Stage: Critic")
        critique = await self.critic.run(state, on_event=on_event)
        state.critiques.append(critique)
        self.emit(on_event, {"type": "stage_complete", "agent": "critic", "progress": 80, "output": critique})

        if critique.get("needs_more_research"):
            logger.info("Critic requested supplementary research")

        # Step 7: Writer
        state.current_stage = "writer"
        state.progress = 90
        self.emit(on_event, {"type": "stage_start", "agent": "writer", "progress": 90})
        logger.info("Stage: Writer")
        report = await self.writer.run(state, on_event=on_event)
        state.final_report = report
        self.emit(on_event, {"type": "stage_complete", "agent": "writer", "progress": 92, "output": {"title": report.get("title", ""), "executive_summary": report.get("executive_summary", "")}})

        # Step 8: Validator
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
