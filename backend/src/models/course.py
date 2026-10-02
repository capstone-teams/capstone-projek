import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class CourseStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class Course(BaseModel):
    __tablename__ = "course"

    instructor_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    rps_id: Mapped[str] = mapped_column(
        ForeignKey("rps.id"),
        nullable=False,
    )

    sortorder: Mapped[int] = mapped_column(
        nullable=False,
    )

    fullname: Mapped[str] = mapped_column(
        String(254),
        nullable=False,
    )
    
    shortname: Mapped[str] = mapped_column(
        String(254),
        nullable=False,
    )

    code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    semester: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    status: Mapped[CourseStatus] = mapped_column(
        Enum(CourseStatus, name="course_status"),
        nullable=False,
        default=CourseStatus.DRAFT,
    )

    moodle_course_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
