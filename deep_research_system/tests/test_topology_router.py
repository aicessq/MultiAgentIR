from __future__ import annotations

import pytest

from app.topology.router import TopologyRouter


@pytest.fixture
def router() -> TopologyRouter:
    return TopologyRouter()


def test_industry_report_routes_to_hierarchical(router: TopologyRouter) -> None:
    topo, template = router.route("industry_report")
    assert topo == "hierarchical"


def test_open_question_routes_to_debate(router: TopologyRouter) -> None:
    topo, template = router.route("open_question")
    assert topo == "debate"


def test_strategy_decision_routes_to_debate(router: TopologyRouter) -> None:
    topo, template = router.route("strategy_decision")
    assert topo == "debate"


def test_company_analysis_routes_to_hierarchical(router: TopologyRouter) -> None:
    topo, template = router.route("company_analysis")
    assert topo == "hierarchical"


def test_unknown_defaults_to_hierarchical(router: TopologyRouter) -> None:
    topo, template = router.route("unknown_type")
    assert topo == "hierarchical"
