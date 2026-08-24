"""Token cost calculation and hard preflight/runtime budget enforcement."""

from __future__ import annotations

from dataclasses import dataclass


class BudgetExceededError(RuntimeError):
    """Raised before a call that would exceed the configured hard cap."""


@dataclass(frozen=True)
class Price:
    input_per_million: float
    output_per_million: float

    def cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (
            prompt_tokens * self.input_per_million + completion_tokens * self.output_per_million
        ) / 1_000_000


@dataclass
class BudgetGuard:
    hard_cap_usd: float
    spent_usd: float = 0.0

    def preflight(self, projected_total_usd: float) -> None:
        """Reject a planned experiment whose pilot-based projection exceeds the cap."""
        if projected_total_usd > self.hard_cap_usd:
            raise BudgetExceededError(
                f"Projected cost ${projected_total_usd:.2f} exceeds hard cap "
                f"${self.hard_cap_usd:.2f}"
            )

    def reserve(self, projected_call_usd: float) -> None:
        """Reject a next call if even its conservative projection exceeds the cap."""
        if self.spent_usd + projected_call_usd > self.hard_cap_usd:
            raise BudgetExceededError("Next model call would exceed the hard budget cap")

    def record(self, actual_call_usd: float) -> None:
        self.spent_usd += actual_call_usd
        if self.spent_usd > self.hard_cap_usd + 1e-9:
            raise BudgetExceededError("Provider-reported cost exceeded the hard budget cap")
