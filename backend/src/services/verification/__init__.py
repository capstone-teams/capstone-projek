"""Moodle verification: domain, error, repository, dan service (BE-21.2)."""

from src.services.verification.domain import (
    Discrepancy,
    DiscrepancyType,
    VerificationResultRecord,
    compare_course,
)
from src.services.verification.errors import (
    NO_EXECUTION_TO_VERIFY,
    VerificationNotFoundError,
    VerificationPreconditionError,
)
from src.services.verification.service import VerificationService

__all__ = [
    "NO_EXECUTION_TO_VERIFY",
    "Discrepancy",
    "DiscrepancyType",
    "VerificationNotFoundError",
    "VerificationPreconditionError",
    "VerificationResultRecord",
    "VerificationService",
    "compare_course",
]