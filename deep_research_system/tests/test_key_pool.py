from __future__ import annotations

import pytest

from app.model_pool.circuit_breaker import KeyCircuitBreaker
from app.schemas.model import KeyStatus


def test_circuit_breaker_healthy() -> None:
    cb = KeyCircuitBreaker()
    assert cb.get_status("key1") == KeyStatus.HEALTHY


def test_circuit_breaker_open_after_failures() -> None:
    cb = KeyCircuitBreaker()
    for _ in range(3):
        cb.record_failure("key1")
    assert cb.get_status("key1") == KeyStatus.OPEN


def test_circuit_breaker_half_open() -> None:
    cb = KeyCircuitBreaker()
    cb.record_failure("key1")
    assert cb.get_status("key1") == KeyStatus.HALF_OPEN


def test_circuit_breaker_success_resets() -> None:
    cb = KeyCircuitBreaker()
    cb.record_failure("key1")
    cb.record_success("key1")
    assert cb.get_status("key1") == KeyStatus.HEALTHY


def test_circuit_breaker_disable() -> None:
    cb = KeyCircuitBreaker()
    cb.disable("key1")
    assert cb.get_status("key1") == KeyStatus.DISABLED
