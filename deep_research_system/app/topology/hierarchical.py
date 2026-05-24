from __future__ import annotations

import asyncio
import logging
from typing import Callable

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


def _wrap_agent_name(on_event: EventCallback, wrapped_name: str) -> EventCallback:
    """Wrap an event callback to rename agent-specific events.

    Used for parallel sub-tasks (searcher_sq_1, reader_sq_2) and
    composite stages (supplementary_search, repair_writer) so each
    gets its own node in the frontend topology.
    """
    def wrapped_event(event: dict) -> None:
        agent = event.get("agent", "")
        # Only rename agent-level events (not stage_start/stage_complete from topology)
        if agent and event.get("type") in (
            "agent_model_selected", "agent_thinking", "agent_output",
            "agent_stream_token", "subtask_complete",
        ):
            event = {**event, "agent": wrapped_name}
        BaseTopology.emit(on_event, event)
    return wrapped_event


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

        # Step 2: Searcher (parallel, each sub-question gets its own agent node)
        state.current_stage = "searcher"
        state.progress = 25
        self.emit(on_event, {"type": "stage_start", "agent": "searcher", "progress": 25})
        logger.info(f"Stage: Searcher ({len(state.plan)} sub-questions)")
        searcher_tasks = []
        sq_ids = []
        for sq in state.plan:
            sq_id = sq["id"]
            sq_ids.append(sq_id)
            agent_name = f"searcher_{sq_id}"
            searcher = self.searcher_cls()
            sq_state = state.model_copy(deep=True)
            sq_state.plan = [sq]
            # Emit stage_start for this subtask agent
            self.emit(on_event, {"type": "stage_start", "agent": agent_name, "progress": 25})
            wrapped_on_event = _wrap_agent_name(on_event, agent_name)
            searcher_tasks.append(searcher.run(sq_state, on_event=wrapped_on_event))

        search_results = await asyncio.gather(*searcher_tasks, return_exceptions=True)
        for sq_id, sq, result in zip(sq_ids, state.plan, search_results):
            agent_name = f"searcher_{sq_id}"
            if isinstance(result, Exception):
                logger.error(f"Searcher failed for {sq_id}: {result}")
                state.errors.append({"stage": "searcher", "sq_id": sq_id, "error": str(result)})
                self.emit(on_event, {"type": "stage_complete", "agent": agent_name, "progress": 30})
            else:
                state.sub_results[sq_id] = result
                for source in result.get("sources", []):
                    url = source.get("url", "")
                    if url:
                        state.source_registry[url] = source
                self.emit(on_event, {
                    "type": "stage_complete",
                    "agent": agent_name,
                    "progress": 30,
                    "output": result,
                })
        self.emit(on_event, {"type": "stage_complete", "agent": "searcher", "progress": 35, "output": {"results": list(state.sub_results.keys())}})

        # Step 3: Reader (parallel, each sub-question gets its own agent node)
        state.current_stage = "reader"
        state.progress = 45
        self.emit(on_event, {"type": "stage_start", "agent": "reader", "progress": 45})
        logger.info("Stage: Reader")
        reader_tasks = []
        reader_sq_ids = []
        for sq_id, sq_data in state.sub_results.items():
            reader_sq_ids.append(sq_id)
            agent_name = f"reader_{sq_id}"
            reader = self.reader_cls()
            sq_state = state.model_copy(deep=True)
            sq_state.sub_results = {sq_id: sq_data}
            self.emit(on_event, {"type": "stage_start", "agent": agent_name, "progress": 45})
            wrapped_on_event = _wrap_agent_name(on_event, agent_name)
            reader_tasks.append(reader.run(sq_state, on_event=wrapped_on_event))

        reader_results = await asyncio.gather(*reader_tasks, return_exceptions=True)
        for sq_id, result in zip(reader_sq_ids, reader_results):
            agent_name = f"reader_{sq_id}"
            if isinstance(result, Exception):
                logger.error(f"Reader failed for {sq_id}: {result}")
                self.emit(on_event, {"type": "stage_complete", "agent": agent_name, "progress": 50})
            else:
                state.sub_results[sq_id] = {**state.sub_results[sq_id], **result}
                self.emit(on_event, {
                    "type": "stage_complete",
                    "agent": agent_name,
                    "progress": 50,
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
        if isinstance(analysis, dict):
            state.claim_graph = analysis.get("claims", [])
            for claim in state.claim_graph:
                state.claim_audit.append({
                    "claim_id": claim.get("claim_id", ""),
                    "claim_text": claim.get("claim_text", ""),
                    "evidence_ids": claim.get("evidence_ids", []),
                    "analyzer_confidence": claim.get("confidence", 0.5),
                    "critic_findings": [],
                    "writer_sections_used": [],
                    "validator_status": "unverified",
                })
        self.emit(on_event, {"type": "stage_complete", "agent": "analyzer", "progress": 65, "output": analysis})

        # Step 5: Critic
        state.current_stage = "critic"
        state.progress = 75
        self.emit(on_event, {"type": "stage_start", "agent": "critic", "progress": 75})
        logger.info("Stage: Critic")
        critique = await self.critic.run(state, on_event=on_event)
        state.critiques.append(critique)
        if isinstance(critique, dict):
            for finding in critique.get("findings", []):
                target_id = finding.get("target_id", "")
                for audit_entry in state.claim_audit:
                    if audit_entry["claim_id"] == target_id:
                        audit_entry["critic_findings"].append(finding)
        self.emit(on_event, {"type": "stage_complete", "agent": "critic", "progress": 80, "output": critique})

        # Step 6: Critic -> Searcher loop (supplementary research)
        from app.core.config import get_config
        topo_cfg = get_config().topology.get("hierarchical", {})
        max_loops = topo_cfg.get("max_research_loops", 1)

        if critique.get("needs_more_research") or critique.get("overall_assessment") == "needs_research":
            loop_count = 0
            while loop_count < max_loops:
                loop_count += 1
                logger.info(f"Critic->Searcher loop {loop_count}/{max_loops}")
                self.emit(on_event, {"type": "stage_start", "agent": "supplementary_search", "progress": 80 + loop_count})

                supplementary_queries = []
                for finding in critique.get("findings", []):
                    supplementary_queries.extend(finding.get("suggested_search_queries", []))

                if not supplementary_queries:
                    logger.info("No supplementary queries from critic, breaking loop")
                    self.emit(on_event, {"type": "stage_complete", "agent": "supplementary_search", "progress": 82 + loop_count})
                    break

                supp_sq = {
                    "id": f"supp_{loop_count}",
                    "question": "补充研究：" + "；".join(supplementary_queries[:3]),
                    "search_queries": supplementary_queries[:3],
                    "priority": 1,
                }
                supp_state = state.model_copy(deep=True)
                supp_state.plan = [supp_sq]
                searcher = self.searcher_cls()
                # Wrap events so inner searcher shows as supplementary_search
                supp_on_event = _wrap_agent_name(on_event, "supplementary_search")
                supp_result = await searcher.run(supp_state, on_event=supp_on_event)

                if not isinstance(supp_result, Exception):
                    state.sub_results[f"supp_{loop_count}"] = supp_result
                    for source in supp_result.get("sources", []):
                        url = source.get("url", "")
                        if url:
                            state.source_registry[url] = source

                # Re-run analyzer with expanded evidence (wrap as supplementary_search)
                analysis = await self.analyzer.run(state, on_event=supp_on_event)
                state.analyses.append(analysis)
                if isinstance(analysis, dict):
                    state.claim_graph = analysis.get("claims", [])

                # Re-run critic (wrap as supplementary_search)
                critique = await self.critic.run(state, on_event=supp_on_event)
                state.critiques.append(critique)

                self.emit(on_event, {"type": "stage_complete", "agent": "supplementary_search", "progress": 82 + loop_count, "output": supp_result})

                if not critique.get("needs_more_research"):
                    logger.info("Critic satisfied after supplementary research")
                    break

        # Step 7: Writer
        state.current_stage = "writer"
        state.progress = 90
        self.emit(on_event, {"type": "stage_start", "agent": "writer", "progress": 90})
        logger.info("Stage: Writer")
        report = await self.writer.run(state, on_event=on_event)
        state.final_report = report
        self.emit(on_event, {"type": "stage_complete", "agent": "writer", "progress": 92, "output": {"title": report.get("title", ""), "executive_summary": report.get("executive_summary", "")}})

        # Step 8: Validator + Repair Loop
        state.current_stage = "validator"
        state.progress = 95
        self.emit(on_event, {"type": "stage_start", "agent": "validator", "progress": 95})
        logger.info("Stage: Validator")
        validation = await self.validator.run(state, on_event=on_event)
        self.emit(on_event, {"type": "stage_complete", "agent": "validator", "progress": 98, "output": validation})

        # Repair loop: if validation fails or score is low, re-run writer with repair context
        max_repair_loops = topo_cfg.get("max_repair_loops", 2)
        repair_attempt = 0
        while repair_attempt < max_repair_loops:
            is_valid = validation.get("valid", False)
            score = validation.get("score", 100)
            if is_valid and score >= 85:
                logger.info(f"Validation passed after {repair_attempt} repair(s) (valid={is_valid}, score={score})")
                break
            repair_attempt += 1
            agent_name = f"repair_writer_{repair_attempt}"
            logger.info(f"Repair loop {repair_attempt}/{max_repair_loops} (valid={is_valid}, score={score})")
            self.emit(on_event, {
                "type": "stage_start", "agent": agent_name,
                "progress": 96, "repair_count": repair_attempt,
            })

            state.repair_context = validation.get("issues", [])
            repair_on_event = _wrap_agent_name(on_event, agent_name)
            report = await self.writer.run(state, on_event=repair_on_event)
            state.final_report = report

            # Re-validate silently (no agent events — avoids overwriting repair node state)
            validation = await self.validator.run(state, on_event=None)
            logger.info(f"Repair {repair_attempt} validation: valid={validation.get('valid')}, score={validation.get('score')}")
            self.emit(on_event, {
                "type": "stage_complete", "agent": agent_name,
                "progress": 97, "repair_count": repair_attempt, "output": validation,
            })
            # Push intermediate report to frontend after each repair
            self.emit(on_event, {
                "type": "report_update", "agent": "writer",
                "progress": 97, "output": state.final_report,
            })

        state.repair_context = []

        if not validation.get("valid"):
            logger.warning(f"Validation failed after {repair_attempt} repair(s): {validation.get('issues')}")

        # Emit final report so frontend has the latest version
        self.emit(on_event, {
            "type": "report_update",
            "agent": "writer",
            "progress": 99,
            "output": state.final_report,
        })

        state.current_stage = "completed"
        state.progress = 100
        return state
