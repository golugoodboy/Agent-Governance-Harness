
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


class ApprovalRegistry:

    def __init__(self, db_path="data/approval_registry.db"):
        self.db_path = str(db_path)

        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        self._initialize_database()

    def _connect(self):
        connection = sqlite3.connect(
            self.db_path,
            timeout=10,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_database(self):
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS approval_requests (
                    approval_id TEXT PRIMARY KEY,
                    audit_run_id TEXT NOT NULL,
                    proposal_fingerprint TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

    def create_pending(
        self,
        approval_id,
        audit_run_id,
        proposal_fingerprint,
        action,
    ):
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")

            existing = connection.execute(
                """
                SELECT * FROM approval_requests
                WHERE approval_id = ?
                """,
                (approval_id,),
            ).fetchone()

            if existing:
                same_request = (
                    existing["audit_run_id"] == audit_run_id
                    and existing["proposal_fingerprint"]
                    == proposal_fingerprint
                    and existing["action"] == action
                )

                if not same_request:
                    raise ValueError(
                        "Approval ID already belongs to another request"
                    )

                return dict(existing)

            connection.execute(
                """
                INSERT INTO approval_requests (
                    approval_id,
                    audit_run_id,
                    proposal_fingerprint,
                    action,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    approval_id,
                    audit_run_id,
                    proposal_fingerprint,
                    action,
                    now,
                    now,
                ),
            )

            return dict(
                connection.execute(
                    """
                    SELECT * FROM approval_requests
                    WHERE approval_id = ?
                    """,
                    (approval_id,),
                ).fetchone()
            )

    def get_approval(self, approval_id):
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM approval_requests
                WHERE approval_id = ?
                """,
                (approval_id,),
            ).fetchone()

        return dict(row) if row else None

    def consume_approval(
        self,
        approval_id,
        proposal_fingerprint,
        approved,
    ):
        """
        Atomically consume a pending approval.

        An approval can only transition out of pending once.
        """

        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")

            row = connection.execute(
                """
                SELECT * FROM approval_requests
                WHERE approval_id = ?
                """,
                (approval_id,),
            ).fetchone()

            if row is None:
                raise ValueError("Unknown approval ID")

            if row["status"] != "pending":
                raise ValueError(
                    f"Approval is no longer pending: {row['status']}"
                )

            if row["proposal_fingerprint"] != proposal_fingerprint:
                connection.execute(
                    """
                    UPDATE approval_requests
                    SET status = 'invalidated',
                        updated_at = ?
                    WHERE approval_id = ?
                    """,
                    (now, approval_id),
                )

                return {
                    "valid": False,
                    "status": "invalidated",
                    "reason": "Proposal fingerprint mismatch",
                }

            new_status = "consumed" if approved else "rejected"

            connection.execute(
                """
                UPDATE approval_requests
                SET status = ?,
                    updated_at = ?
                WHERE approval_id = ?
                    AND status = 'pending'
                """,
                (new_status, now, approval_id),
            )

            return {
                "valid": True,
                "status": new_status,
                "reason": "Approval accepted"
                if approved
                else "Approval rejected",
            }
