
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta


class ApprovalRegistry:

    def __init__(
        self,
        db_path="data/approval_registry.db",
        ttl_seconds=900,
        now_provider=None,
    ):
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than zero")

        self.db_path = str(db_path)
        self.ttl_seconds = ttl_seconds
        self._now = now_provider or (
            lambda: datetime.now(timezone.utc)
        )

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
                    updated_at TEXT NOT NULL,
                    expires_at TEXT
                )
            """)

            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(approval_requests)"
                ).fetchall()
            }

            # Migrate existing databases safely.
            if "expires_at" not in columns:
                connection.execute("""
                    ALTER TABLE approval_requests
                    ADD COLUMN expires_at TEXT
                """)

            # Give existing records an expiration based on
            # their original creation time.
            rows = connection.execute("""
                SELECT approval_id, created_at
                FROM approval_requests
                WHERE expires_at IS NULL
            """).fetchall()

            for row in rows:
                created_at = datetime.fromisoformat(
                    row["created_at"]
                )

                expires_at = (
                    created_at
                    + timedelta(seconds=self.ttl_seconds)
                ).isoformat()

                connection.execute("""
                    UPDATE approval_requests
                    SET expires_at = ?
                    WHERE approval_id = ?
                """, (expires_at, row["approval_id"]))

    def _expire_if_needed(self, connection, row):
        if row["status"] != "pending":
            return dict(row)

        expires_at = datetime.fromisoformat(
            row["expires_at"]
        )

        if self._now() < expires_at:
            return dict(row)

        now = self._now().isoformat()

        connection.execute("""
            UPDATE approval_requests
            SET status = 'expired',
                updated_at = ?
            WHERE approval_id = ?
              AND status = 'pending'
        """, (now, row["approval_id"]))

        updated = connection.execute("""
            SELECT *
            FROM approval_requests
            WHERE approval_id = ?
        """, (row["approval_id"],)).fetchone()

        return dict(updated)

    def create_pending(
        self,
        approval_id,
        audit_run_id,
        proposal_fingerprint,
        action,
    ):
        now = self._now()

        expires_at = (
            now + timedelta(seconds=self.ttl_seconds)
        )

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")

            existing = connection.execute("""
                SELECT *
                FROM approval_requests
                WHERE approval_id = ?
            """, (approval_id,)).fetchone()

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

                return self._expire_if_needed(
                    connection,
                    existing,
                )

            connection.execute("""
                INSERT INTO approval_requests (
                    approval_id,
                    audit_run_id,
                    proposal_fingerprint,
                    action,
                    status,
                    created_at,
                    updated_at,
                    expires_at
                )
                VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)
            """, (
                approval_id,
                audit_run_id,
                proposal_fingerprint,
                action,
                now.isoformat(),
                now.isoformat(),
                expires_at.isoformat(),
            ))

            row = connection.execute("""
                SELECT *
                FROM approval_requests
                WHERE approval_id = ?
            """, (approval_id,)).fetchone()

            return dict(row)

    def get_approval(self, approval_id):
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")

            row = connection.execute("""
                SELECT *
                FROM approval_requests
                WHERE approval_id = ?
            """, (approval_id,)).fetchone()

            if row is None:
                return None

            return self._expire_if_needed(
                connection,
                row,
            )

    def consume_approval(
        self,
        approval_id,
        proposal_fingerprint,
        approved,
    ):
        """
        Atomically consume a pending approval.

        An approval can only transition out of pending once.
        Expired approvals cannot be consumed.
        """

        now = self._now().isoformat()

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")

            row = connection.execute("""
                SELECT *
                FROM approval_requests
                WHERE approval_id = ?
            """, (approval_id,)).fetchone()

            if row is None:
                raise ValueError("Unknown approval ID")

            row = self._expire_if_needed(
                connection,
                row,
            )

            if row["status"] == "expired":
                return {
                    "valid": False,
                    "status": "expired",
                    "reason": "Approval request has expired",
                }

            if row["status"] != "pending":
                raise ValueError(
                    f"Approval is no longer pending: {row['status']}"
                )

            if row["proposal_fingerprint"] != proposal_fingerprint:
                connection.execute("""
                    UPDATE approval_requests
                    SET status = 'invalidated',
                        updated_at = ?
                    WHERE approval_id = ?
                """, (now, approval_id))

                return {
                    "valid": False,
                    "status": "invalidated",
                    "reason": "Proposal fingerprint mismatch",
                }

            new_status = (
                "consumed" if approved else "rejected"
            )

            connection.execute("""
                UPDATE approval_requests
                SET status = ?,
                    updated_at = ?
                WHERE approval_id = ?
                  AND status = 'pending'
            """, (new_status, now, approval_id))

            return {
                "valid": True,
                "status": new_status,
                "reason": (
                    "Approval accepted"
                    if approved
                    else "Approval rejected"
                ),
            }
