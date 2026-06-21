"""Shared reducers for Graph States.

Reducers must be:
- Side-effect free
- Repeatable
- Deduplicating
- Order-preserving where relevant
"""

from __future__ import annotations


def merge_unique_strings(existing: list[str], updates: list[str]) -> list[str]:
    """Merge two lists, keeping only unique items, preserving order.

    Used for: evidence_ids, document_ids, completed_subtask_ids
    """
    result = list(existing)
    for item in updates:
        if item not in result:
            result.append(item)
    return result


def merge_dict(existing: dict, updates: dict) -> dict:
    """Merge two dicts, with updates taking precedence.

    Used for: source_registry, branch_result_refs, position_result_refs
    """
    return {**existing, **updates}


def append_list(existing: list, updates: list) -> list:
    """Append new items to existing list.

    Used for: warnings, errors, audit_trail
    """
    return existing + updates


def merge_usage(existing: dict, updates: dict) -> dict:
    """Merge usage counters.

    Used for: token_usage, model_usage, budget tracking
    """
    result = dict(existing)
    for key, value in updates.items():
        if key in result:
            result[key] = result[key] + value
        else:
            result[key] = value
    return result


def merge_branch_results(existing: dict[str, str], updates: dict[str, str]) -> dict[str, str]:
    """Merge branch results, with newer results taking precedence.

    Used for: branch_result_refs, position_result_refs
    """
    return {**existing, **updates}


def max_int(existing: int, updates: int) -> int:
    """Take the maximum of two integers.

    Used for: research_round, debate_round, repair_count
    """
    return max(existing, updates)


def override(existing, updates):
    """Always take the update value.

    Used for: authoritative_analysis_id, authoritative_report_id, status
    """
    return updates
