import argparse
import json

from app.audit_logger import AuditLogger


def inspect_audit(db_path: str) -> int:
    logger = AuditLogger(db_path)
    events = logger.list_events()
    integrity = logger.verify_integrity()

    print("\n" + "=" * 76)
    print("AI AGENT GOVERNANCE HARNESS — AUDIT INSPECTOR")
    print("=" * 76)
    print(f"Database: {db_path}")
    print(f"Events:   {len(events)}")
    print(f"Integrity: {'VALID' if integrity['valid'] else 'INVALID'}")
    print(f"Details:   {integrity['reason']}")

    if not events:
        print("\nNo audit events found.")
        return 0 if integrity["valid"] else 1

    print("\nEVENT HISTORY")
    print("-" * 76)

    for event in events:
        print(f"\nEvent #{event['id']} | {event['event_type']}")
        print(f"Timestamp:   {event['timestamp']}")
        print(f"Action:      {event['action']}")
        print(f"Decision:    {event['decision']}")
        print(f"Risk score:  {event['risk_score']}")
        print(f"Approval:    {event['approval_status']}")
        print(f"Execution:   {event['execution_status']}")
        print(f"Fingerprint: {event['proposal_fingerprint']}")
        print(f"Idempotency: {event['idempotency_key']}")
        print(f"Event hash:  {event['event_hash']}")
        print(f"Details:     {json.dumps(event['details'], ensure_ascii=False)}")

    print("\n" + "=" * 76)

    return 0 if integrity["valid"] else 1


def main():
    parser = argparse.ArgumentParser(
        description="Inspect the AI governance SQLite audit trail."
    )
    parser.add_argument(
        "--db",
        default="data/audit_log.db",
        help="Path to the SQLite audit database",
    )
    args = parser.parse_args()

    raise SystemExit(inspect_audit(args.db))


if __name__ == "__main__":
    main()
