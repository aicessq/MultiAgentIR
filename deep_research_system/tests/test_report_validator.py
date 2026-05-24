"""Tests for the deterministic report validator."""

from app.validators.report_validator import validate_report


def _make_report(**overrides):
    base = {
        "title": "Test Report",
        "as_of_date": "2026-05-24",
        "executive_summary": "This is a test executive summary with enough content to pass.",
        "sections": [
            {
                "heading": "Section 1",
                "content": "A" * 150,
                "claim_ids": ["clm_001"],
                "key_claims": [
                    {"claim_id": "clm_001", "sentence": "Test claim", "evidence_ids": ["ev_001"], "confidence": "high", "source_urls": ["https://example.com"]}
                ],
                "citations": ["https://example.com"],
            },
            {
                "heading": "Section 2",
                "content": "B" * 150,
                "claim_ids": ["clm_002"],
                "key_claims": [],
                "citations": ["https://example.com"],
            },
            {
                "heading": "Section 3",
                "content": "C" * 150,
                "claim_ids": ["clm_003"],
                "key_claims": [],
                "citations": ["https://example.com"],
            },
        ],
        "risk_register": [
            {"risk": "Risk 1", "mechanism": "Mechanism 1", "evidence_claim_ids": ["clm_001"], "likelihood": "medium", "impact": "high"},
            {"risk": "Risk 2", "mechanism": "Mechanism 2", "evidence_claim_ids": ["clm_002"], "likelihood": "low", "impact": "medium"},
            {"risk": "Risk 3", "mechanism": "Mechanism 3", "evidence_claim_ids": ["clm_003"], "likelihood": "high", "impact": "high"},
        ],
        "limitations": ["Limitation 1"],
    }
    base.update(overrides)
    return base


def _make_claim_graph():
    return [
        {"claim_id": "clm_001", "claim_text": "Claim 1", "evidence_ids": ["ev_001"], "confidence": 0.9},
        {"claim_id": "clm_002", "claim_text": "Claim 2", "evidence_ids": ["ev_002"], "confidence": 0.7},
        {"claim_id": "clm_003", "claim_text": "Claim 3", "evidence_ids": ["ev_003"], "confidence": 0.5},
    ]


def _make_source_registry():
    return {
        "https://example.com": {"url": "https://example.com", "title": "Example", "credibility_score": 0.8, "domain": "example.com", "reliability": "medium"},
    }


def test_valid_report_passes():
    report = _make_report()
    result = validate_report(report, _make_claim_graph(), _make_source_registry())
    assert result["valid"] is True
    assert len([i for i in result["issues"] if i["severity"] == "high"]) == 0


def test_missing_title_fails():
    report = _make_report(title="")
    result = validate_report(report, _make_claim_graph(), _make_source_registry())
    assert result["valid"] is False
    assert any("标题" in i["problem"] for i in result["issues"])


def test_missing_as_of_date_fails():
    report = _make_report(as_of_date="")
    result = validate_report(report, _make_claim_graph(), _make_source_registry())
    assert result["valid"] is False
    assert any("as_of_date" in i["problem"] for i in result["issues"])


def test_invalid_as_of_date_format_fails():
    report = _make_report(as_of_date="2026/05/24")
    result = validate_report(report, _make_claim_graph(), _make_source_registry())
    assert result["valid"] is False
    assert any("格式" in i["problem"] for i in result["issues"])


def test_placeholder_in_content_fails():
    report = _make_report()
    report["sections"][0]["content"] = "This section has undefined content."
    result = validate_report(report, _make_claim_graph(), _make_source_registry())
    assert result["valid"] is False
    assert any("占位符" in i["problem"] for i in result["issues"])


def test_placeholder_null_in_content_fails():
    report = _make_report()
    report["sections"][1]["content"] = "The value is null here."
    result = validate_report(report, _make_claim_graph(), _make_source_registry())
    assert result["valid"] is False


def test_placeholder_tbd_in_content_fails():
    report = _make_report()
    report["sections"][2]["content"] = "TBD - to be determined later."
    result = validate_report(report, _make_claim_graph(), _make_source_registry())
    assert result["valid"] is False


def test_short_content_fails():
    report = _make_report()
    report["sections"][0]["content"] = "Too short."
    result = validate_report(report, _make_claim_graph(), _make_source_registry())
    assert any("过短" in i["problem"] for i in result["issues"])


def test_invalid_claim_id_fails():
    report = _make_report()
    report["sections"][0]["claim_ids"] = ["clm_nonexistent"]
    result = validate_report(report, _make_claim_graph(), _make_source_registry())
    assert result["valid"] is False
    assert any("不存在" in i["problem"] for i in result["issues"])


def test_unregistered_citation_warns():
    report = _make_report()
    report["sections"][0]["citations"] = ["https://unknown.com"]
    result = validate_report(report, _make_claim_graph(), _make_source_registry())
    assert any("未注册" in i["problem"] for i in result["issues"])


def test_insufficient_risk_register_fails():
    report = _make_report()
    report["risk_register"] = [{"risk": "Only one", "mechanism": "M", "evidence_claim_ids": ["clm_001"]}]
    result = validate_report(report, _make_claim_graph(), _make_source_registry())
    assert result["valid"] is False
    assert any("不完整" in i["problem"] for i in result["issues"])


def test_risk_missing_fields_fails():
    report = _make_report()
    report["risk_register"] = [
        {"risk": "", "mechanism": "M", "evidence_claim_ids": ["clm_001"]},
        {"risk": "R2", "mechanism": "", "evidence_claim_ids": ["clm_002"]},
        {"risk": "R3", "mechanism": "M", "evidence_claim_ids": []},
    ]
    result = validate_report(report, _make_claim_graph(), _make_source_registry())
    assert any("risk" in i["problem"].lower() or "evidence_claim_ids" in i["problem"] for i in result["issues"])


def test_low_quality_domain_for_core_claim_fails():
    claim_graph = [
        {"claim_id": "clm_001", "claim_text": "Revenue", "claim_type": "financial_metric", "evidence_ids": ["ev_001"], "confidence": 0.9},
        {"claim_id": "clm_002", "claim_text": "Other", "evidence_ids": ["ev_002"], "confidence": 0.7},
        {"claim_id": "clm_003", "claim_text": "More", "evidence_ids": ["ev_003"], "confidence": 0.5},
    ]
    source_registry = {
        "https://facebook.com/post1": {"url": "https://facebook.com/post1", "domain": "facebook.com", "reliability": "low"},
        "https://example.com": {"url": "https://example.com", "domain": "example.com", "reliability": "medium"},
    }
    report = _make_report()
    # Point the core claim's key_claim to the low-quality source
    report["sections"][0]["key_claims"][0]["source_urls"] = ["https://facebook.com/post1"]
    result = validate_report(report, claim_graph, source_registry)
    assert any("低质量" in i["problem"] for i in result["issues"])


def test_date_conflict_warns():
    source_registry = {
        "https://example.com": {"url": "https://example.com", "publish_date": "2026-06-15", "domain": "example.com"},
    }
    report = _make_report(as_of_date="2026-05-24")
    result = validate_report(report, _make_claim_graph(), source_registry)
    assert any("晚于" in w["problem"] for w in result["warnings"])


def test_missing_executive_summary_fails():
    report = _make_report(executive_summary="")
    result = validate_report(report, _make_claim_graph(), _make_source_registry())
    assert result["valid"] is False
    assert any("执行摘要" in i["problem"] for i in result["issues"])
