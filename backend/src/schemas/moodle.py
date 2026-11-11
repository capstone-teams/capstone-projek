
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ApiErrorBody",
    "ApiErrorResponse",
    "CreateMoodleCourseRequest",
    "FunctionAvailabilityResponse",
    "MoodleCourseContentsResponse",
    "MoodleCourseListResponse",
    "MoodleCourseResponse",
    "MoodleModuleResponse",
    "MoodleSectionResponse",
    "MoodleStatusResponse",
    "SaveMoodleSectionRequest",
]


class ApiErrorBody(BaseModel):
    code: str
    message: str
    details: list[dict] = Field(default_factory=list)


class ApiErrorResponse(BaseModel):
    error: ApiErrorBody


class FunctionAvailabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    available: bool


class MoodleStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str = Field(description="CONNECTED bila backend terhubung ke Moodle")
    connected: bool
    message: str
    site_name: str
    release: str
    version: str
    all_functions_available: bool
    functions: list[FunctionAvailabilityResponse]


class MoodleCourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="ID course di Moodle (sama dengan moodle_course_id)")
    moodle_course_id: int
    fullname: str
    shortname: str
    visible: bool
    summary: str
    category_id: int | None = None
    category: str | None = None


class MoodleCourseListResponse(BaseModel):
    courses: list[MoodleCourseResponse]


class MoodleModuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    moodle_module_id: int
    name: str
    modname: str
    visible: bool
    description: str
    url: str | None = Field(
        default=None, description="Alamat tujuan untuk module URL (learning resource)."
    )
    content: str | None = Field(default=None, description="Isi HTML untuk module Page.")


class MoodleSectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    moodle_section_id: int
    section_number: int
    name: str
    summary: str
    visible: bool
    modules: list[MoodleModuleResponse]


class MoodleCourseContentsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    moodle_course_id: int
    sections: list[MoodleSectionResponse]


class CreateMoodleCourseRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    fullname: str = Field(min_length=1, max_length=254)
    shortname: str = Field(min_length=1, max_length=100)
    category_id: int = Field(default=1, ge=1)


class AddCourseSectionRequest(BaseModel):
    """Tambah section dari Edit mode halaman course; nama kosong menjadi "Pertemuan N"."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(default="", max_length=255)


class RenameCourseSectionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)


class SaveMoodleSectionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    section_number: int | None = Field(default=None, ge=0)
