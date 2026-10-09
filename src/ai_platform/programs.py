from typing import Literal

import dspy


class TicketIntent(dspy.Signature):
    """Classify a customer support message into one intent."""

    message: str = dspy.InputField()
    label: Literal["billing", "technical", "account", "other"] = dspy.OutputField()