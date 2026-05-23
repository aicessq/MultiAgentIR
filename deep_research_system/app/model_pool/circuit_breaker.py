from __future__ import annotations

from app.schemas.model import KeyStatus

FAILURE_THRESHOLD = 3
RECOVERY_TIMEOUT_S = 60


class KeyCircuitBreaker:
    def __init__(self) -> None:
        self._failure_counts: dict[str, int] = {}
        self._statuses: dict[str, KeyStatus] = {}
        self._last_failure: dict[str, float] = {}

    def get_status(self, key_id: str) -> KeyStatus:
        status = self._statuses.get(key_id, KeyStatus.HEALTHY)
        if status == KeyStatus.OPEN:
            import time
            last = self._last_failure.get(key_id, 0)
            if time.time() - last > RECOVERY_TIMEOUT_S:
                self._statuses[key_id] = KeyStatus.HALF_OPEN
                return KeyStatus.HALF_OPEN
        return status

    def record_success(self, key_id: str) -> None:
        self._failure_counts[key_id] = 0
        self._statuses[key_id] = KeyStatus.HEALTHY

    def record_failure(self, key_id: str) -> None:
        import time
        count = self._failure_counts.get(key_id, 0) + 1
        self._failure_counts[key_id] = count
        self._last_failure[key_id] = time.time()
        if count >= FAILURE_THRESHOLD:
            self._statuses[key_id] = KeyStatus.OPEN
        else:
            self._statuses[key_id] = KeyStatus.HALF_OPEN

    def disable(self, key_id: str) -> None:
        self._statuses[key_id] = KeyStatus.DISABLED

    def reset(self, key_id: str) -> None:
        self._failure_counts[key_id] = 0
        self._statuses[key_id] = KeyStatus.HEALTHY
