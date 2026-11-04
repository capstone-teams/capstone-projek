"""Endpoint setup dosen (BE-10.2).

Router ini hanya menangani urusan HTTP: kontrak endpoint, dependency, dan
pemetaan domain → DTO. Validasi aturan bisnis serta penyimpanan berada di
:mod:`src.services.instructor`.

Kontrak mengikuti design-api §7 (terbit pada BE-06.4): satu alur untuk seluruh
setup dosen, ``GET``/``PUT /instructors/me/setup``, hanya untuk role
``INSTRUCTOR`` (mekanisme BE-03.4). ``PUT`` bersifat parsial — hanya field yang
dikirim yang diubah. Nilai ``null`` pada field profile berarti "tidak diubah";
``additional_prompt`` dikosongkan dengan mengirim string kosong.

Seluruh kesalahan input pada endpoint ini dilaporkan sebagai ``422
INVALID_REQUEST`` dengan ``details`` per field, termasuk tipe data yang salah
(design-api §7.2). Karena itu body divalidasi oleh schema, lalu kegagalan
validasi FastAPI diterjemahkan oleh :class:`_InvalidRequestRoute` — tanpa itu,
kesalahan tipe akan keluar sebagai ``422 VALIDATION_FAILED`` milik handler
global dan menyimpang dari kontrak.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute

from src.schemas.errors import ErrorResponse
from src.schemas.instructor import (
    ActivityConfiguration,
    InstructorProfileSetup,
    InstructorSetupResponse,
    InstructorSetupUpdate,
)
from src.services.dependencies import get_instructor_service, require_roles
from src.services.instructor import (
    ACTIVITY_FIELDS,
    InstructorSetup,
    InstructorSetupService,
    InstructorSetupValidationError,
)
from src.services.user.domain import User
from src.services.user.enums import UserRole

class _InvalidRequestRoute(APIRoute):
    """Route yang melaporkan body cacat sebagai ``422 INVALID_REQUEST``.

    Default aplikasi memakai ``422 VALIDATION_FAILED`` untuk kesalahan schema
    (design-api §18), sedangkan kontrak setup dosen (§7.2) menyatakan seluruh
    kesalahan input — termasuk tipe data — sebagai ``INVALID_REQUEST``. Bentuk
    error-nya tetap amplop standar, hanya kodenya yang berbeda.
    """

    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        handler = super().get_route_handler()

        async def translate_validation_error(request: Request) -> Response:
            try:
                return await handler(request)
            except RequestValidationError as exc:
                raise InstructorSetupValidationError(_issues_from(exc)) from exc

        return translate_validation_error


def _issues_from(exc: RequestValidationError) -> list[tuple[str, str]]:
    """Ringkas error validasi request menjadi pasangan ``(field, message)``."""
    issues: list[tuple[str, str]] = []
    for error in exc.errors():
        location = [
            str(part)
            for part in error.get("loc", ())
            if part not in ("body", "query", "path", "header")
        ]
        issues.append(
            (".".join(location) or "body", str(error.get("msg", "Nilai tidak valid.")))
        )
    return issues


router = APIRouter(
    prefix="/instructors",
    tags=["Instructor Setup"],
    route_class=_InvalidRequestRoute,
)

# Policy instructor-only, sama seperti endpoint RPS (design-api §22).
instructor_only = require_roles(UserRole.INSTRUCTOR)

SETUP_PATH = "/me/setup"

INVALID_SETUP_EXAMPLE = {
    "error": {
        "code": "INVALID_REQUEST",
        "message": "Pengaturan dosen tidak valid.",
        "details": [
            {
                "field": "additional_prompt",
                "message": "maksimal 2000 karakter",
            }
        ],
    }
}

INVALID_SETUP_RESPONSE = {
    "model": ErrorResponse,
    "description": (
        "Nilai atau tipe field tidak sah (batas panjang Additional Prompt, tidak "
        "ada jenis aktivitas aktif, atau tipe data salah). `error.details` memuat "
        "satu entri per field bermasalah."
    ),
    "content": {"application/json": {"example": INVALID_SETUP_EXAMPLE}},
}

AUTHORIZATION_RESPONSE = {
    "model": ErrorResponse,
    "description": "Role bukan `INSTRUCTOR`; response tidak menyebut role yang dibutuhkan.",
}

AUTHENTICATION_RESPONSE = {
    "model": ErrorResponse,
    "description": "Request tanpa access token yang valid.",
}

SETUP_RESPONSES = {
    401: AUTHENTICATION_RESPONSE,
    403: AUTHORIZATION_RESPONSE,
    422: INVALID_SETUP_RESPONSE,
}


def _to_response(setup: InstructorSetup, fallback_updated_at: datetime) -> InstructorSetupResponse:
    """Petakan domain setup ke DTO response."""
    return InstructorSetupResponse(
        instructor_profile=InstructorProfileSetup(
            teaching_style=setup.profile.teaching_style,
            expertise=setup.profile.expertise,
            delivery_preference=setup.profile.delivery_preference,
            language_preference=setup.profile.language_preference,
        ),
        additional_prompt=setup.activity.additional_prompt or "",
        activity_configuration=ActivityConfiguration(
            learning_material=setup.activity.learning_material,
            learning_resource=setup.activity.learning_resource,
            assignment=setup.activity.assignment,
            quiz=setup.activity.quiz,
        ),
        updated_at=setup.updated_at or fallback_updated_at,
    )


def _profile_changes(profile: InstructorProfileSetup | None) -> dict[str, str]:
    """Field profile yang dikirim (nilai ``null`` berarti tidak diubah)."""
    if profile is None:
        return {}
    return {
        name: value
        for name in (
            "teaching_style",
            "expertise",
            "delivery_preference",
            "language_preference",
        )
        if (value := getattr(profile, name)) is not None
    }


def _activity_changes(payload: InstructorSetupUpdate) -> dict[str, object]:
    """Flag aktivitas dan additional prompt yang benar-benar dikirim.

    ``model_fields_set`` dipakai supaya ``false`` yang dikirim eksplisit tidak
    tertukar dengan field yang tidak dikirim (nilai bawaannya ``true`` untuk
    learning material).
    """
    changes: dict[str, object] = {}
    activity = payload.activity_configuration
    if activity is not None:
        changes.update(
            {
                name: getattr(activity, name)
                for name in ACTIVITY_FIELDS
                if name in activity.model_fields_set
            }
        )
    if payload.additional_prompt is not None:
        changes["additional_prompt"] = payload.additional_prompt
    return changes


@router.get(SETUP_PATH, response_model=InstructorSetupResponse, responses=SETUP_RESPONSES)
async def get_my_setup(
    current_user: User = Depends(instructor_only),
    service: InstructorSetupService = Depends(get_instructor_service),
) -> InstructorSetupResponse:
    """Setup dosen yang sedang login.

    Dosen yang belum pernah menyimpan setup menerima nilai default (learning
    material aktif, jenis aktivitas lain nonaktif, profile kosong), bukan 404 —
    halaman setup langsung dapat ditampilkan. ``updated_at`` pada kasus itu
    memakai waktu akun dosen dibuat, karena setup default berlaku sejak saat itu.
    """
    setup = await service.get_setup(current_user.id)
    return _to_response(setup, current_user.created_at or datetime.now(timezone.utc))


@router.put(SETUP_PATH, response_model=InstructorSetupResponse, responses=SETUP_RESPONSES)
async def update_my_setup(
    payload: InstructorSetupUpdate,
    current_user: User = Depends(instructor_only),
    service: InstructorSetupService = Depends(get_instructor_service),
) -> InstructorSetupResponse:
    """Ubah sebagian setup dosen.

    Hanya field yang dikirim yang diubah; body kosong ``{}`` mengembalikan setup
    yang sekarang tanpa menulis apa pun. ``null`` pada field profile berarti
    "tidak diubah", sedangkan ``additional_prompt: ""`` mengosongkan prompt.

    Tidak ada yang tersimpan bila satu field saja tidak valid: hasil gabungan
    divalidasi lebih dulu, sehingga mematikan aktivitas terakhir yang masih aktif
    ditolak dengan detail field.
    """
    setup = await service.update_setup(
        current_user.id,
        profile_changes=_profile_changes(payload.instructor_profile),
        activity_changes=_activity_changes(payload),
    )
    return _to_response(setup, current_user.created_at or datetime.now(timezone.utc))
