"""Shared agent control-flow exceptions."""


class InterruptAgentFlowError(Exception):
    """Raised to interrupt the agent flow and add messages."""

    def __init__(self, *messages: dict):
        self.messages = messages
        super().__init__()


# Keep the original name as a compatibility alias for existing integrations.
InterruptAgentFlow = InterruptAgentFlowError


class Submitted(InterruptAgentFlowError):  # noqa: N818 - Persisted as the public exit-status value.
    """Raised when the agent has completed its task."""


class LimitsExceeded(InterruptAgentFlowError):  # noqa: N818 - Persisted as the public exit-status value.
    """Raised when the agent has exceeded its cost or step limit."""


class TimeExceeded(LimitsExceeded):
    """Raised when the agent has exceeded its wall-clock time limit."""


class UserInterruption(InterruptAgentFlowError):  # noqa: N818 - Persisted as the public exit-status value.
    """Raised when the user interrupts the agent."""


class FormatError(InterruptAgentFlowError):
    """Raised when the LM's output is not in the expected format."""
