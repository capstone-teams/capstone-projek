from __future__ import annotations

from dataclasses import dataclass

NON_IDEMPOTENT_FUNCTIONS = frozenset({"core_course_create_courses"})


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 0.5
    max_delay: float = 5.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts harus minimal 1")
        if self.base_delay < 0 or self.max_delay < 0:
            raise ValueError("delay tidak boleh negatif")

    def delay_for(self, attempt: int) -> float:
        return min(self.base_delay * 2 ** (attempt - 1), self.max_delay)