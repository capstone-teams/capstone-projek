from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class Category(BaseModel):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    visible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    moodle_category_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
