from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class MoodleEntityMapping(BaseModel):
    """Pemetaan entity internal aplikasi ke entity Moodle (BE-04.3).

    Dua unique constraint menjaga pemetaan tetap satu-ke-satu:
    - satu entity internal hanya boleh punya satu Moodle ID,
    - satu Moodle ID hanya boleh dimiliki satu entity internal.
    """

    __tablename__ = "moodle_entity_mappings"
    __table_args__ = (
        UniqueConstraint("entity_type", "internal_id", name="uq_moodle_mapping_internal"),
        UniqueConstraint("entity_type", "moodle_id", name="uq_moodle_mapping_moodle"),
    )

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    internal_id: Mapped[str] = mapped_column(String(255), nullable=False)
    moodle_id: Mapped[int] = mapped_column(Integer, nullable=False)