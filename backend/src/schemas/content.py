from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ==========================================
# INPUT CONTEXT
# ==========================================

class RPSAnalysisContext(BaseModel):
    version: int
    course_identity: dict[str, Any] | None = None
    learning_outcomes: dict[str, Any] | None = None
    objectives: dict[str, Any] | None = None
    topics: dict[str, Any] | None = None
    weekly_distribution: dict[str, Any] | None = None
    teaching_methods: dict[str, Any] | None = None
    assessments: dict[str, Any] | None = None
    references: dict[str, Any] | None = None


class WeeklyContentContext(BaseModel):
    week_number: int = Field(ge=1)
    week_type: str = "regular"
    title: str | None = None
    materials: list[str] = Field(default_factory=list)


class WeekContext(BaseModel):
    rps_id: str
    rps_analysis: RPSAnalysisContext
    week_number: int = Field(ge=1)
    week_data: WeeklyContentContext

    @property
    def week(self) -> int:
        return self.week_number

    def to_prompt_dict(self) -> dict:
        return {
            "rps_id": self.rps_id,
            "rps_analysis": self.rps_analysis.model_dump(mode="json"),
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
