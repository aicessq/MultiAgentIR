"""Deterministic report validator — runs before LLM checker to catch hard failures."""

from __future__ import annotations

import re
from datetime import datetime

PLACEHOLDER_PATTERNS = [
    r"\bundefined\b",
    r"\bnull\b",
    r"\bNone\b",
    r"\bTBD\b",
    r"\bTODO\b",
    r"待补充",
    r"占位",
    r"\bN/A\b",
    r"\bNaN\b",
]

LOW_QUALITY_DOMAINS = [
    "facebook.com",
    "zhihu.com",
    "tieba.baidu.com",
    "toutiao.com",
    "baijiahao.baidu.com",
]

CORE_CLAIM_TYPES = {"financial_metric", "sales_metric", "market_share", "regulatory_claim"}

MIN_SECTION_CONTENT_LENGTH = 100
MIN_RISK_REGISTER_SIZE = 3


def validate_report(
    report: dict,
    claim_graph: list[dict],
    source_registry: dict[str, dict],
) -> dict:
    """Run deterministic checks on a report.

    Returns:
        dict with keys: valid (bool), issues (list[dict]), warnings (list[dict])
    """
    issues: list[dict] = []
    warnings: list[dict] = []
    claim_ids_in_graph = {c.get("claim_id", "") for c in claim_graph}

    # 1. Basic structure
    if not report.get("title"):
        issues.append(_issue("high", "report", "缺少报告标题", "补充 title 字段"))

    raw_summary = report.get("executive_summary", "")
    # executive_summary can be a string or a dict {"content": "...", "claim_ids": [...]}
    if isinstance(raw_summary, dict):
        summary_text = raw_summary.get("content", "")
    else:
        summary_text = str(raw_summary)
    if not summary_text:
        issues.append(_issue("high", "report", "缺少执行摘要", "补充 executive_summary 字段"))

    # 2. as_of_date
    as_of_date = report.get("as_of_date", "")
    if not as_of_date:
        issues.append(_issue("high", "report", "缺少 as_of_date", "补充 as_of_date 字段，格式 YYYY-MM-DD"))
    else:
        try:
            datetime.strptime(as_of_date, "%Y-%m-%d")
        except ValueError:
            issues.append(_issue("high", "report", f"as_of_date 格式无效: {as_of_date}", "使用 YYYY-MM-DD 格式"))

    # 3. Sections
    sections = report.get("sections", [])
    if len(sections) < 3:
        issues.append(_issue("medium", "report", f"章节数不足（{len(sections)}个）", "至少需要 3 个章节"))

    placeholder_re = re.compile("|".join(PLACEHOLDER_PATTERNS), re.IGNORECASE)

    for section in sections:
        heading = section.get("heading", "?")
        content = section.get("content", "")

        # 3a. Placeholder detection
        if placeholder_re.search(content):
            issues.append(_issue("high", heading, f"章节'{heading}'内容包含占位符", "移除占位符，用实际内容替换"))

        # 3b. Minimum content length
        if len(content) < MIN_SECTION_CONTENT_LENGTH:
            issues.append(_issue("medium", heading, f"章节'{heading}'内容过短（{len(content)}字符）", f"至少需要 {MIN_SECTION_CONTENT_LENGTH} 字符"))

        # 3c. claim_ids exist in claim_graph
        for cid in section.get("claim_ids", []):
            if cid not in claim_ids_in_graph:
                issues.append(_issue("high", heading, f"章节'{heading}'引用了不存在的 claim_id: {cid}", "移除无效 claim_id 或补充对应 claim"))

        # 3d. key_claims validation
        for kc in section.get("key_claims", []):
            kc_id = kc.get("claim_id", "")
            if kc_id and kc_id not in claim_ids_in_graph:
                issues.append(_issue("high", heading, f"key_claim 引用了不存在的 claim_id: {kc_id}", "修正 claim_id"))
            if kc_id and not kc.get("evidence_ids"):
                issues.append(_issue("medium", heading, f"key_claim {kc_id} 缺少 evidence_ids", "补充 evidence_ids"))

        # 3e. Citations in source_registry
        for url in section.get("citations", []):
            if url not in source_registry:
                issues.append(_issue("medium", heading, f"引用了未注册的来源: {url}", "移除未注册来源或将其加入 source_registry"))

    # 4. Placeholder in executive_summary
    if summary_text and placeholder_re.search(summary_text):
        issues.append(_issue("high", "executive_summary", "执行摘要包含占位符", "移除占位符"))

    # 5. Risk register
    risk_register = report.get("risk_register", [])
    if len(risk_register) < MIN_RISK_REGISTER_SIZE:
        issues.append(_issue("high", "risk_register", f"风险登记册不完整（{len(risk_register)}项，至少需要 {MIN_RISK_REGISTER_SIZE} 项）", "补充风险项"))
    for i, risk in enumerate(risk_register):
        if not risk.get("risk"):
            issues.append(_issue("medium", "risk_register", f"风险项 {i+1} 缺少 risk 字段", "补充风险名称"))
        if not risk.get("mechanism"):
            issues.append(_issue("medium", "risk_register", f"风险项 {i+1} 缺少 mechanism 字段", "补充风险机制"))
        if not risk.get("evidence_claim_ids"):
            issues.append(_issue("medium", "risk_register", f"风险项 {i+1} 缺少 evidence_claim_ids", "补充支撑 claim_id"))

    # 6. Low-quality domain check for core claims
    _check_source_quality(report, source_registry, claim_graph, issues, warnings)

    # 7. as_of_date vs source publish_date
    if as_of_date:
        _check_date_conflicts(as_of_date, source_registry, warnings)

    has_high = any(i["severity"] == "high" for i in issues)
    return {"valid": not has_high, "issues": issues, "warnings": warnings}


def _check_source_quality(
    report: dict,
    source_registry: dict[str, dict],
    claim_graph: list[dict],
    issues: list[dict],
    warnings: list[dict],
) -> None:
    """Check that core claims are not supported by low-quality sources."""
    # Build claim_type -> claim_id mapping
    core_claim_ids = set()
    for claim in claim_graph:
        if claim.get("claim_type", "general") in CORE_CLAIM_TYPES:
            core_claim_ids.add(claim.get("claim_id", ""))

    if not core_claim_ids:
        return

    # Build claim_id -> source_urls from key_claims
    core_source_urls: set[str] = set()
    for section in report.get("sections", []):
        for kc in section.get("key_claims", []):
            if kc.get("claim_id") in core_claim_ids:
                core_source_urls.update(kc.get("source_urls", []))

    # Check each core source against low-quality domains
    for url in core_source_urls:
        source = source_registry.get(url, {})
        domain = source.get("domain", "")
        if not domain and url:
            # Extract domain from URL
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc.lower()
            except Exception:
                pass
        for lq_domain in LOW_QUALITY_DOMAINS:
            if lq_domain in domain:
                issues.append(_issue(
                    "high", "source_quality",
                    f"核心事实使用了低质量来源: {url} (domain: {domain})",
                    "替换为高质量来源或将该 claim 降级为低置信度",
                ))
                break


def _check_date_conflicts(
    as_of_date: str,
    source_registry: dict[str, dict],
    warnings: list[dict],
) -> None:
    """Warn if source publish_date is after as_of_date."""
    try:
        cutoff = datetime.strptime(as_of_date, "%Y-%m-%d")
    except ValueError:
        return

    for url, source in source_registry.items():
        pub_date = source.get("publish_date") or source.get("published_at")
        if not pub_date:
            continue
        try:
            pub_dt = datetime.strptime(str(pub_date)[:10], "%Y-%m-%d")
            if pub_dt > cutoff:
                warnings.append({
                    "location": "source_registry",
                    "problem": f"来源 {url} 的发布日期 ({pub_date}) 晚于 as_of_date ({as_of_date})",
                    "fix": "移除该来源或更新 as_of_date",
                })
        except (ValueError, TypeError):
            pass


def _issue(severity: str, location: str, problem: str, fix: str) -> dict:
    return {"severity": severity, "location": location, "problem": problem, "fix": fix}
