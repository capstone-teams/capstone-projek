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

    topic: str = Field(min_length=1)
    sub_cpmk: list[str] = Field(default_factory=list)
    material: str = Field(min_length=1)


class GeneratedContentData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    week_number: int = Field(ge=1)
    sections: list[ContentSection] = Field(min_length=1)


class GeneratedLearningMaterial(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    title: str = Field(min_length=1, max_length=255)
    content_type: GeneratedContentType = (
        GeneratedContentType.LEARNING_MATERIAL
    )
    content_data: GeneratedContentData | None = None
# from typing import Any
#
# from pydantic import BaseModel, ConfigDict, Field
#
#
# class RPSAnalysisContext(BaseModel):
#     version: int
#     course_identity: dict[str, Any] | None = None
#     learning_outcomes: dict[str, Any] | None = None
#     objectives: dict[str, Any] | None = None
#     topics: dict[str, Any] | None = None
#     weekly_distribution: dict[str, Any] | None = None
#     teaching_methods: dict[str, Any] | None = None
#     assessments: dict[str, Any] | None = None
#     references: dict[str, Any] | None = None
#
#
# class WeeklyContentContext(BaseModel):
#     week_number: int = Field(ge=1)
#     week_type: str = "regular"
#     title: str | None = None
#     materials: list[str] = Field(default_factory=list)
#
#
# class WeekContext(BaseModel):
#     """Konteks RPS untuk generasi materi satu minggu."""
#
#     rps_id: str
#     rps_analysis: RPSAnalysisContext
#     week_number: int = Field(ge=1)
#     week_data: WeeklyContentContext
#
#     @property
#     def week(self) -> int:
#         return self.week_number
#
#     def to_prompt_dict(self) -> dict[str, Any]:
#         return {
#             "rps_id": self.rps_id,
#             "rps_analysis": self.rps_analysis.model_dump(mode="json"),
#             "week_number": self.week_number,
#             "week_data": self.week_data.model_dump(mode="json"),
#         }
#
#
# class ContentOutputModel(BaseModel):
#     model_config = ConfigDict(
#         extra="forbid",
#         str_strip_whitespace=True,
#     )
#
#
# class LearningItem(ContentOutputModel):
#     name: str = Field(min_length=1, max_length=255)
#     material_learning: str = Field(min_length=1)
#
#
# class GeneratedLearningMaterial(ContentOutputModel):
#     content_learning: list[LearningItem] = Field(min_length=1)
