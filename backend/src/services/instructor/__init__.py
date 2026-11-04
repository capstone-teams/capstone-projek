"""Setup dosen (BE-10): Instructor Profile, Additional Prompt, Activity Configuration.

Paket ini melayani endpoint setup dosen dan agent tanpa mereka menyentuh ORM:

- :class:`~src.services.instructor.domain.InstructorSetup` — aturan nilai setup;
- :class:`~src.services.instructor.service.InstructorSetupService` — ambil,
  simpan, dan bangun konteks dosen untuk agent;
- :class:`~src.services.instructor.repository.InstructorSetupRepository` — akses
  data, hanya dipanggil service.

Batas panjang Additional Prompt berasal dari environment
(``INSTRUCTOR_ADDITIONAL_PROMPT_MAX_LENGTH``).
"""

from src.services.instructor.context import (
    ACADEMIC_SOURCE_OF_TRUTH,
    CONTEXT_ROLE,
    instructor_context_to_yaml,
    to_agent_context,
)
from src.services.instructor.domain import (
    ACTIVITY_FIELDS,
    ActivityConfiguration,
    InstructorProfile,
    InstructorSetup,
    normalize_setup,
)
from src.services.instructor.errors import (
    InstructorSetupError,
    InstructorSetupValidationError,
)
from src.services.instructor.repository import InstructorSetupRepository
from src.services.instructor.service import InstructorSetupService

__all__ = [
    "ACADEMIC_SOURCE_OF_TRUTH",
    "ACTIVITY_FIELDS",
    "CONTEXT_ROLE",
    "ActivityConfiguration",
    "InstructorProfile",
    "InstructorSetup",
    "InstructorSetupError",
    "InstructorSetupRepository",
    "InstructorSetupService",
    "InstructorSetupValidationError",
    "instructor_context_to_yaml",
    "normalize_setup",
    "to_agent_context",
]
