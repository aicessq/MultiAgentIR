"""SQLite-backed model slot configuration service."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import aiosqlite

from app.core.config import BASE_DIR

logger = logging.getLogger(__name__)

DB_PATH = BASE_DIR / "data" / "config.db"

SLOTS = ["search", "analysis", "reasoning", "writing"]

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS model_slots (
    slot TEXT PRIMARY KEY,
    model_name TEXT NOT NULL DEFAULT '',
    api_key TEXT NOT NULL DEFAULT '',
    api_base TEXT NOT NULL DEFAULT '',
    updated_at TEXT DEFAULT (datetime('now'))
)
"""


class ConfigService:
    def __init__(self) -> None:
        self._db_path = DB_PATH

    async def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(str(self._db_path)) as db:
            await db.execute(CREATE_TABLE_SQL)
            # Seed default slots if empty
            cursor = await db.execute("SELECT COUNT(*) FROM model_slots")
            count = (await cursor.fetchone())[0]
            if count == 0:
                for slot in SLOTS:
                    await db.execute(
                        "INSERT INTO model_slots (slot, model_name, api_key, api_base) VALUES (?, ?, ?, ?)",
                        (slot, "", "", ""),
                    )
                await db.commit()

    async def get_all(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(str(self._db_path)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT slot, model_name, api_key, api_base FROM model_slots")
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                result.append({
                    "slot": row["slot"],
                    "model_name": row["model_name"],
                    "api_key": self._mask_key(row["api_key"]),
                    "api_base": row["api_base"],
                    "has_key": bool(row["api_key"]),
                })
            return result

    async def get_raw(self, slot: str) -> dict[str, str] | None:
        async with aiosqlite.connect(str(self._db_path)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT slot, model_name, api_key, api_base FROM model_slots WHERE slot = ?", (slot,)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "slot": row["slot"],
                "model_name": row["model_name"],
                "api_key": row["api_key"],
                "api_base": row["api_base"],
            }

    async def update(self, slot: str, model_name: str, api_key: str, api_base: str) -> None:
        async with aiosqlite.connect(str(self._db_path)) as db:
            await db.execute(
                """INSERT INTO model_slots (slot, model_name, api_key, api_base, updated_at)
                   VALUES (?, ?, ?, ?, datetime('now'))
                   ON CONFLICT(slot) DO UPDATE SET
                     model_name=excluded.model_name,
                     api_key=CASE WHEN excluded.api_key = '' THEN model_slots.api_key ELSE excluded.api_key END,
                     api_base=excluded.api_base,
                     updated_at=datetime('now')""",
                (slot, model_name, api_key, api_base),
            )
            await db.commit()

    async def reset(self) -> None:
        async with aiosqlite.connect(str(self._db_path)) as db:
            for slot in SLOTS:
                await db.execute(
                    "UPDATE model_slots SET model_name='', api_key='', api_base='', updated_at=datetime('now') WHERE slot=?",
                    (slot,),
                )
            await db.commit()

    def _mask_key(self, key: str) -> str:
        if not key or len(key) < 8:
            return ""
        return key[:4] + "*" * (len(key) - 8) + key[-4:]


_config_service: ConfigService | None = None


async def get_config_service() -> ConfigService:
    global _config_service
    if _config_service is None:
        _config_service = ConfigService()
        await _config_service.initialize()
    return _config_service
