import enum

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class UserRole(str, enum.Enum):
    INSTRUCTOR = "INSTRUCTOR"
    STUDENT = "STUDENT"
    ADMIN = "ADMIN"


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class User(BaseModel):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        nullable=False,
    )

    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus),
        nullable=False,
    )
