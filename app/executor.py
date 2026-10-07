from app.schemas import ActionProposal, Decision
from app.governor import Governor
from app.tool_normalizer import normalize_toolname
from app.tool_registry import TOOLS
from app.tools import *
from app.recovery_manager import RecoveryManager, RecoveryAction


class Executor:

    def __init__(self):

        self.governor = Governor()
        self.recovery_manager = RecoveryManager()

        # Track attempts for each execution
        self.attempt_history = {}

    def execute(self, proposal: ActionProposal):

        # --------------------------------------------------
        # 1. Normalize the tool name
        # --------------------------------------------------

        canonical_action = normalize_toolname(proposal.action)

        proposal.action = canonical_action

        print(
            f"\n[EXECUTOR] Normalized action: "
            f"{proposal.action}"
        )

        # --------------------------------------------------
        # 2. Governance check
        # --------------------------------------------------

        decision = self.governor.evaluate(proposal)

        print("\n[EXECUTOR] Governor Decision")
        print(decision)

        # --------------------------------------------------
        # 3. Block if Governor does not allow execution
        # --------------------------------------------------

        if decision.decision != Decision.ALLOW:

            return {
                "status": "blocked",
                "decision": decision.decision,
                "reason": decision.reason
            }

        # --------------------------------------------------
        # 4. Check whether tool exists
        # --------------------------------------------------

        tool = TOOLS.get(proposal.action)

        if tool is None:

            return {
                "status": "blocked",
                "reason": f"Unknown tool: {proposal.action}"
            }

        # --------------------------------------------------
        # 5. Execute with recovery
        # --------------------------------------------------

        attempt = 1

        while True:

            print(
                f"\n[EXECUTOR] Attempt {attempt} "
                f"for {proposal.action}"
            )

            result = self._execute_tool(
                tool,
                proposal
            )

            # --------------------------------------------------
            # SUCCESS
            # --------------------------------------------------

            if result.get("status") == "success":

                print(
                    "[EXECUTOR] Tool execution successful."
                )

                return result

            # --------------------------------------------------
            # FAILURE
            # --------------------------------------------------

            error = result.get(
                "error",
                "unknown_error"
            )

            recovery_action = self.recovery_manager.decide(
                error=error,
                attempt=attempt
            )

            print(
                f"[RECOVERY] "
                f"error={error} | "
                f"action={recovery_action.value}"
            )

            # --------------------------------------------------
            # RETRY
            # --------------------------------------------------

            if recovery_action == RecoveryAction.RETRY:

                attempt += 1

                continue

            # --------------------------------------------------
            # STOP
            # --------------------------------------------------

            if recovery_action == RecoveryAction.STOP:

                return {
                    "status": "failed",
                    "error": error,
                    "attempts": attempt,
                    "reason": "Non-retryable failure."
                }

            # --------------------------------------------------
            # MAX RETRIES
            # --------------------------------------------------

            if recovery_action == RecoveryAction.FAIL:

                return {
                    "status": "failed",
                    "error": error,
                    "attempts": attempt,
                    "reason": (
                        "Maximum retry attempts "
                        "exceeded."
                    )
                }

    # ==========================================================
    # TOOL EXECUTION
    # ==========================================================

    def _execute_tool(self, tool, proposal):

        """
        Execute the actual tool.

        This method keeps tool-specific argument handling
        separate from the recovery logic.
        """

        try:

            # ----------------------------------------------
            # Search Web
            # ----------------------------------------------

            if proposal.action == "search_web":

                return tool(proposal.target)

            # ----------------------------------------------
            # Send Email
            # ----------------------------------------------

            if proposal.action == "send_email":

                return tool(proposal.target)

            # ----------------------------------------------
            # Delete File
            # ----------------------------------------------

            if proposal.action == "delete_file":

                return tool(proposal.target)

            # ----------------------------------------------
            # Transfer Money
            # ----------------------------------------------

            if proposal.action == "transfer_money":

                return tool(
                    proposal.target,
                    proposal.amount
                )

            # ----------------------------------------------
            # Unstable Tool
            # ----------------------------------------------

            if proposal.action == "unstable_tool":

                return self._execute_unstable_tool(
                    proposal
                )

            # ----------------------------------------------
            # Unknown tool
            # ----------------------------------------------

            return {
                "status": "error",
                "error": (
                    f"No execution handler for "
                    f"{proposal.action}"
                )
            }

        except Exception as exc:

            return {
                "status": "error",
                "error": str(exc)
            }

    # ==========================================================
    # SIMULATED UNSTABLE TOOL
    # ==========================================================

    def _execute_unstable_tool(self, proposal):

        """
        Simulates temporary tool failures.

        temporary_failure:
            Attempt 1 -> failure
            Attempt 2 -> success

        timeout:
            Every attempt -> timeout
        """

        key = proposal.target

        self.attempt_history[key] = (
            self.attempt_history.get(key, 0) + 1
        )

        current_attempt = self.attempt_history[key]

        # ----------------------------------------------
        # Temporary failure
        # ----------------------------------------------

        if proposal.target == "temporary_failure":

            if current_attempt == 1:

                return {
                    "status": "error",
                    "error": "temporary_error"
                }

            return {
                "status": "success",
                "tool": "unstable_tool",
                "result": (
                    "Operation recovered "
                    "successfully."
                )
            }

        # ----------------------------------------------
        # Permanent timeout
        # ----------------------------------------------

        if proposal.target == "timeout":

            return {
                "status": "error",
                "error": "timeout"
            }

        # ----------------------------------------------
        # Normal successful execution
        # ----------------------------------------------

        return {
            "status": "success",
            "tool": "unstable_tool",
            "result": (
                f"Operation completed "
                f"for {proposal.target}"
            )
        }