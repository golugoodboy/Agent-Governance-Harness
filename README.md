## V0.6 — Governed LangGraph Agent Loop

### Overview

V0.6 integrates LangGraph and a Hugging Face Inference API model into the AI Agent Governance Harness. The LLM proposes actions, while the existing governance layer remains responsible for authorization and execution.

### Key Features

- **LLM-based action proposals:** Generate structured action proposals from natural-language requests.
- **Governance enforcement:** Route proposals through the existing permission, risk, and argument-validation controls.
- **Controlled execution:** Execute permitted actions through the existing Executor.
- **Bounded agent loop:** Allow follow-up proposals while enforcing a configurable maximum step count.
- **Safe termination:** Stop after blocked or failed execution, proposal-generation errors, or reaching the step limit.
- **Audit logging:** Record proposals, governance outcomes, execution statuses, and workflow termination events.
- **Recovery:** Retain the existing V0.5 transient-error retry and recovery behavior.

### Architecture

User Request → LLM Proposal → Governance Checks → Executor → Result Evaluation → Follow-up Decision

The workflow terminates when the task is complete, an action fails or is blocked, proposal generation fails, or the maximum number of steps is reached.

### Safety Principle

The LLM proposes actions; it does not independently authorize or execute them. All real tool execution must pass through the governance harness.

### Testing

Run the test suite:

```bash
pytest -v
```

Tests cover governance outcomes, blocked-action termination, proposal-generation errors, bounded execution loops, and existing harness functionality.

### Limitations

- Tool results may be simulated; a successful test does not imply a real external action occurred.
- LLM-generated confidence values are not calibrated probabilities.
- Human-review decisions require an appropriate approval workflow before execution can proceed.
