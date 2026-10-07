# Agent Governance Harness

A policy-driven governance and reliability layer for AI agents.

The core principle is:

> **The agent can propose an action, but only the harness can authorize and execute it.**

The project is being built incrementally to explore how production-grade AI agents can be governed, secured, validated, recovered, and eventually evaluated.

---

## Architecture

```text
USER
  │
  ▼
AGENT
  │
  ▼
ACTION PROPOSAL
  │
  ▼
TOOL NORMALIZATION
  │
  ▼
PERMISSION ENGINE
  │
  ├── DENY ───────────────► BLOCK
  │
  ▼
ARGUMENT VALIDATION
  │
  ├── INVALID ────────────► BLOCK
  │
  ▼
RISK ENGINE
  │
  ▼
GOVERNOR
  │
  ├── HUMAN_REVIEW ───────► BLOCK / REVIEW
  │
  ▼
EXECUTOR
  │
  ├── SUCCESS ────────────► DONE
  │
  └── FAILURE
        │
        ▼
   RECOVERY MANAGER
        │
        ├── RETRY
        ├── STOP
        └── FAIL
```

---

# Current Version

## V0.5 — Recovery & Retry

The harness can now distinguish between:

- successful execution
- temporary operational failures
- persistent failures
- non-retryable validation failures
- maximum retry limits

### Recovery policy

```text
Transient failure
      │
      ▼
    RETRY
      │
      ├── SUCCESS → DONE
      │
      └── FAILURE
            │
            ▼
       Retry limit
            │
            ▼
           FAIL
```

Non-retryable failures are stopped immediately.

For example:

```text
Invalid email
     ↓
Validation failure
     ↓
BLOCK
```

The harness does not repeatedly retry deterministic failures.

---

# Version History

## V0.1 — Basic Governance

Implemented the initial governance layer.

The agent proposes an action and the Governor determines whether it should be:

- `ALLOW`
- `HUMAN_REVIEW`
- `BLOCK`

---

## V0.2 — Risk Engine

Added risk scoring based on:

- action risk
- agent confidence
- explicit risk level

Example:

```text
Risk Score =
    0.50 × Action Risk
  + 0.20 × Confidence Risk
  + 0.30 × Explicit Risk
```

---

## V0.3 — Tool Permissions & Normalization

Added:

- canonical tool IDs
- tool aliases
- tool normalization
- permission policies
- default-deny behavior
- execution boundary

Example policy:

```python
TOOL_POLICIES = {
    "search_web": Permission.ALLOW,
    "send_email": Permission.ALLOW,
    "delete_file": Permission.HUMAN_REVIEW,
    "transfer_money": Permission.DENY,
}
```

The agent cannot bypass the permission layer by inventing or renaming tools.

---

## V0.4 — Argument Validation

Added validation of tool-specific arguments.

Examples:

### Email

```text
customer@gmail.com
        ↓
VALID
```

```text
not-an-email
        ↓
BLOCK
```

### File operations

Dangerous paths such as path traversal patterns are rejected.

### Money transfers

Transfer arguments are checked for:

- destination
- amount
- positive values
- maximum allowed amount

---

## V0.5 — Recovery & Retry

Added a `RecoveryManager` responsible for deciding what happens after execution failures.

Supported recovery actions:

```text
RETRY
STOP
FAIL
```

Retryable errors include transient failures such as:

- timeout
- network error
- service unavailable
- temporary error

The harness enforces a maximum retry count.

Current limit:

```python
MAX_RETRIES = 3
```

---

# V0.5 Recovery Examples

### Temporary failure

```text
Attempt 1
    ↓
temporary_error
    ↓
RETRY
    ↓
Attempt 2
    ↓
SUCCESS
```

### Persistent failure

```text
Attempt 1
    ↓
timeout
    ↓
RETRY

Attempt 2
    ↓
timeout
    ↓
RETRY

Attempt 3
    ↓
timeout
    ↓
FAIL
```

### Deterministic validation failure

```text
Invalid argument
      ↓
Validation failure
      ↓
BLOCK
      ↓
No retry
```

---

# Project Structure

```text
agent-governance-harness/
│
├── app/
│   ├── main.py
│   ├── agent.py
│   ├── governor.py
│   ├── decisions.py
│   ├── schemas.py
│   │
│   ├── risk_engine.py
│   ├── permission_engine.py
│   ├── argument_validator.py
│   │
│   ├── tool_normalizer.py
│   ├── tool_registry.py
│   ├── tools.py
│   │
│   ├── executor.py
│   └── recovery_manager.py
│
├── tests/
│   ├── test_governor.py
│   ├── test_recovery.py
│   └── test_executor_recovery.py
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

# Design Principles

## 1. Agent ≠ Authority

The agent proposes actions.

The harness decides whether those actions can execute.

```text
Agent → Proposal
Harness → Authorization
Executor → Execution
```

---

## 2. Default Deny

Unknown or unauthorized tools should not execute.

```text
Unknown tool
     ↓
DENY
```

---

## 3. Validate Before Execution

Tool arguments are validated before the executor can perform the action.

```text
Authorization
     ↓
Validation
     ↓
Execution
```

---

## 4. Retry Only Transient Failures

The harness does not retry every failure.

```text
Timeout              → RETRY
Network error        → RETRY
Temporary error      → RETRY

Invalid email        → STOP
Unauthorized tool    → STOP
Unsafe file path     → STOP
Policy violation     → STOP
```

---

## 5. Bounded Recovery

Retries must have a hard limit.

```text
MAX_RETRIES = 3
```

This prevents infinite execution loops.

---

# Testing

Run the complete test suite with:

```bash
pytest
```

The project contains tests covering governance, risk, permissions, validation, and recovery behavior.

Important V0.5 scenarios include:

```text
Temporary failure → Retry → Success

Persistent timeout → Retry → Retry → Fail

Invalid argument → Block without retry
```

---

# Roadmap

## Completed

- [x] V0.1 — Basic Governance
- [x] V0.2 — Risk Engine
- [x] V0.3 — Tool Permissions & Normalization
- [x] V0.4 — Argument Validation
- [x] V0.5 — Recovery & Retry

## Planned

- [ ] V0.6 — LangGraph Integration
- [ ] V0.7 — Evaluation Engine
- [ ] V0.8 — Adversarial Testing
- [ ] V0.9 — Observability
- [ ] V1.0 — Full Agent Governance Harness

---

# Long-Term Vision

The final system is intended to become a reusable governance layer around AI agents.

```text
                    ┌─────────────────────┐
                    │       AI AGENT      │
                    └──────────┬──────────┘
                               │
                         ACTION PROPOSAL
                               │
                               ▼
                    ┌─────────────────────┐
                    │  GOVERNANCE HARNESS │
                    ├─────────────────────┤
                    │ Normalization       │
                    │ Permissions         │
                    │ Validation          │
                    │ Risk Analysis        │
                    │ Authorization       │
                    │ Recovery             │
                    │ Evaluation           │
                    │ Observability       │
                    └──────────┬──────────┘
                               │
                               ▼
                         TOOL EXECUTION
```

The objective is to make agent execution:

**controlled, explainable, testable, recoverable, and safe.**