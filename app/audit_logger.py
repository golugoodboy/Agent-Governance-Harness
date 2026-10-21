
import hashlib
import json
import os
import sqlite3
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GENESIS_HASH = "GENESIS"


class AuditLogger:
    """Store structured audit events in a hash-linked SQLite database."""

    def __init__(self, db_path: str | Path | None = None):
        if db_path is None:
            db_path = os.getenv(
                "AUDIT_DB_PATH",
                "data/audit_log.db",
            )

        self.db_path = Path(db_path)

        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._initialize_database()

    def _connect(self):
        return sqlite3.connect(str(self.db_path), timeout=10)

    def _initialize_database(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    proposal_fingerprint TEXT,
                    action TEXT,
                    decision TEXT,
                    risk_score REAL,
                    approval_status TEXT,
                    execution_status TEXT,
                    details_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _hash_event(event: dict[str, Any]) -> str:
        canonical = json.dumps(
            event,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def append_event(
        self,
        event_type: str,
        *,
        proposal_fingerprint: str | None = None,
        action: str | None = None,
        decision: str | None = None,
        risk_score: float | None = None,
        approval_status: str | None = None,
        execution_status: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not event_type.strip():
            raise ValueError("event_type cannot be empty")

        details_json = json.dumps(
            details or {},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

        with self._connect() as connection:
            # BEGIN IMMEDIATE serializes concurrent writers before
            # they read the previous event's hash.
            connection.execute("BEGIN IMMEDIATE")

            previous = connection.execute(
                """
                SELECT id, event_hash
                FROM audit_events
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()

            previous_id = previous[0] if previous else 0
            previous_hash = previous[1] if previous else GENESIS_HASH

            event = {
                "id": previous_id + 1,
                "event_id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                "proposal_fingerprint": proposal_fingerprint,
                "action": action,
                "decision": decision,
                "risk_score": risk_score,
                "approval_status": approval_status,
                "execution_status": execution_status,
                "details_json": details_json,
                "previous_hash": previous_hash,
            }

            event_hash = self._hash_event(event)

            connection.execute(
                """
                INSERT INTO audit_events (
                    id, event_id, timestamp, event_type,
                    proposal_fingerprint, action, decision, risk_score,
                    approval_status, execution_status, details_json,
                    previous_hash, event_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["id"],
                    event["event_id"],
                    event["timestamp"],
                    event["event_type"],
                    event["proposal_fingerprint"],
                    event["action"],
                    event["decision"],
                    event["risk_score"],
                    event["approval_status"],
                    event["execution_status"],
                    event["details_json"],
                    event["previous_hash"],
                    event_hash,
                ),
            )

            event["event_hash"] = event_hash
            return event

    def list_events(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT * FROM audit_events ORDER BY id"
            ).fetchall()

        events = [dict(row) for row in rows]

        for event in events:
            event["details"] = json.loads(event.pop("details_json"))

        return events

    def verify_integrity(self) -> dict[str, Any]:
        events = self.list_events()
        previous_hash = GENESIS_HASH
        expected_id = 1

        for event in events:
            if event["id"] != expected_id:
                return {
                    "valid": False,
                    "event_id": event["event_id"],
                    "reason": "Missing or reordered event detected",
                }

            if event["previous_hash"] != previous_hash:
                return {
                    "valid": False,
                    "event_id": event["event_id"],
                    "reason": "Previous hash mismatch",
                }

            # Reconstruct exactly the fields originally hashed.
            hash_payload = {
                key: event[key]
                for key in (
                    "id",
                    "event_id",
                    "timestamp",
                    "event_type",
                    "proposal_fingerprint",
                    "action",
                    "decision",
                    "risk_score",
                    "approval_status",
                    "execution_status",
                    "previous_hash",
                )
            }
            hash_payload["details_json"] = json.dumps(
                event["details"],
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )

            calculated_hash = self._hash_event(hash_payload)

            if calculated_hash != event["event_hash"]:
                return {
                    "valid": False,
                    "event_id": event["event_id"],
                    "reason": "Event hash mismatch",
                }

            previous_hash = event["event_hash"]
            expected_id += 1

        return {
            "valid": True,
            "events_checked": len(events),
            "reason": "Audit chain is intact",
        }
