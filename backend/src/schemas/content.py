from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ==========================================
# INPUT CONTEXT
# ==========================================
class WeeklyContentContext(BaseModel):
    week_number: int = Field(ge=1)
    week_type: str = "regular"
    title: str | None = None
    learning_outcomes: Any = None
    topics: list[Any] = Field(default_factory=list)
    methods: list[Any] = Field(default_factory=list)
    assessment: Any = None


class WeekContext(BaseModel):
    course_plan_id: str
    course_plan_week_id: str
    week_number: int = Field(ge=1)
    week_data: WeeklyContentContext

    @property
    def week(self) -> int:
        return self.week_number

    def to_prompt_dict(self) -> dict:
        return {
            "course_plan_id": self.course_plan_id,
            "course_plan_week_id": self.course_plan_week_id,
            "week_number": self.week_number,
            "week_data": self.week_data.model_dump(mode="json"),
        }


# ==========================================
# OUTPUT CONTENT
# ==========================================


class GeneratedContentType(str, Enum):
    LEARNING_MATERIAL = "LEARNING_MATERIAL"


class ContentSection(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class ContentExample(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    title: str = Field(min_length=1)
    description: str = Field(min_length=1)


class ContentReference(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    title: str = Field(min_length=1)
    url: str | None = None


class GeneratedContentData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sections: list[ContentSection] = Field(min_length=1)
    examples: list[ContentExample] = Field(default_factory=list)
    references: list[ContentReference] = Field(default_factory=list)


class GeneratedLearningMaterial(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    title: str = Field(min_length=1, max_length=255)
    content_type: GeneratedContentType = (
        GeneratedContentType.LEARNING_MATERIAL
    )
    content_data: GeneratedContentData
