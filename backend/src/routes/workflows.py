"""Endpoint monitoring workflow dan kanal event real-time (BE-11.3).

Router ini hanya menangani urusan HTTP/WebSocket: kontrak endpoint, dependency,
validasi bentuk input, dan mapping domain → DTO. Aturan lifecycle dan
penulisan event berada di :mod:`src.services.workflow`.

REST endpoint mengikuti design-api §16 dan seluruhnya instructor-only serta
dibatasi pada workflow milik dosen yang login (workflow dosen lain menghasilkan
404 yang sama seperti workflow tidak ada). ``PUT .../moodle-target`` menyimpan
course target Moodle pada workflow (issue BE-11.3).

WebSocket ``/ws/workflows/{workflow_id}`` mengikuti design-api §17: token
dikirim lewat query parameter saat handshake karena browser tidak dapat menyetel
header ``Authorization`` pada WebSocket. Workflow milik dosen lain dan akun
mahasiswa ditolak sebelum ada frame event yang dikirim. Frame yang diterima
klien adalah bentuk ``WorkflowEvent`` yang sama dengan riwayat §16.3.

``ponytail:`` koneksi WebSocket memakai ``AsyncSession`` dari dependency selama
koneksi terbuka (dipakai hanya saat handshake). Satu koneksi per dosen yang
memantau satu workflow membuat ini tidak signifikan; bila jumlah koneksi
monitoring tumbuh, autentikasi handshake dipindah ke session berumur pendek.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Path,
    Query,
    WebSocket,
    WebSocketDisconnect,
)

from src.schemas.workflow import (
    MoodleTargetRequest,
    WorkflowEvent,
    WorkflowEventListResponse,
    WorkflowListResponse,
    WorkflowProgress,
    WorkflowResponse,
    WorkflowStatus,
    WorkflowSummary,
)
from src.services.auth.authorization import RolePolicy
from src.services.auth.errors import AuthDomainError, AuthorizationError
from src.services.auth.service import AuthService
from src.services.dependencies import (
    get_auth_service,
    get_workflow_service,
    require_roles,
)
from src.services.user.domain import User
from src.services.user.enums import UserRole
from src.services.user.validation import ID_LENGTH, SHORTUUID_PATTERN
from src.services.workflow.broker import workflow_event_broker
from src.services.workflow.domain import WorkflowEventRecord, WorkflowRecord, api_status, stage_name
from src.services.workflow.errors import WorkflowDomainError
from src.services.workflow.service import WorkflowService, event_payload

router = APIRouter(tags=["Workflows"])

# Seluruh endpoint monitoring adalah instructor-only (design-api §22: "Monitor
# Agent" hanya untuk dosen).
instructor_only = require_roles(UserRole.INSTRUCTOR)
_instructor_policy = RolePolicy.for_roles(UserRole.INSTRUCTOR)

# Identifier pada path adalah ShortUUID, sehingga bentuk yang salah ditolak
# sebelum menyentuh layer lain (pola yang sama dengan endpoint RPS).
WorkflowIdPath = Annotated[
    str,
    Path(min_length=ID_LENGTH, max_length=ID_LENGTH, pattern=SHORTUUID_PATTERN),
]

# Close code WebSocket untuk kegagalan handshake (rentang 4000–4999 milik
# aplikasi). Client frontend dapat membedakan "login ulang" dari "bukan
# workflow Anda".
WS_UNAUTHORIZED = 4401
WS_FORBIDDEN = 4403
WS_NOT_FOUND = 4404


def _to_summary(workflow: WorkflowRecord) -> WorkflowSummary:
    """Petakan workflow domain ke item daftar workflow."""
    return WorkflowSummary(
        id=workflow.id or "",
        status=WorkflowStatus(api_status(workflow.status)),
        stage=stage_name(workflow.status),
        progress=WorkflowProgress(
            completed=workflow.progress_completed,
            total=workflow.progress_total,
        ),
        rps_id=workflow.rps_id,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


def _to_detail(workflow: WorkflowRecord) -> WorkflowResponse:
    """Petakan workflow domain ke response detail/update."""
    return WorkflowResponse(
        **_to_summary(workflow).model_dump(),
        moodle_course_id=workflow.moodle_course_id,
    )


def _to_event(event: WorkflowEventRecord) -> WorkflowEvent:
    """Petakan event domain ke bentuk yang sama dengan frame WebSocket.

    ``event_payload`` dipakai bersama oleh broker dan riwayat HTTP, sehingga
    kedua kanal tidak dapat menyimpang tanpa terlihat.
    """
    return WorkflowEvent.model_validate(event_payload(event))


@router.get("/workflows", response_model=WorkflowListResponse)
async def list_workflows(
    current_user: User = Depends(instructor_only),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowListResponse:
    """Daftar workflow milik dosen yang login, terbaru lebih dulu (design-api §16.1).

    Scoping owner dilakukan query repository; workflow dosen lain tidak pernah
    termuat. ``status`` adalah status lifecycle API dan ``stage`` adalah tahap
    yang sedang berjalan (``null`` untuk workflow queued/terminal).
    """
    workflows = await service.list_workflows(owner_id=current_user.id)
    return WorkflowListResponse(items=[_to_summary(workflow) for workflow in workflows])


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def read_workflow(
    workflow_id: WorkflowIdPath,
    current_user: User = Depends(instructor_only),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowResponse:
    """Status satu workflow beserta course target Moodle (design-api §16.2).

    Workflow milik dosen lain menghasilkan 404 ``RESOURCE_NOT_FOUND`` yang sama
    seperti workflow yang tidak ada.
    """
    workflow = await service.get_workflow(
        workflow_id=workflow_id, owner_id=current_user.id
    )
    return _to_detail(workflow)


@router.get(
    "/workflows/{workflow_id}/events",
    response_model=WorkflowEventListResponse,
)
async def list_workflow_events(
    workflow_id: WorkflowIdPath,
    current_user: User = Depends(instructor_only),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowEventListResponse:
    """Riwayat event workflow, dari yang paling lama (design-api §16.3).

    Bentuk tiap item sama dengan frame WebSocket §17, sehingga client memakai
    satu parser. Riwayat tetap lengkap setelah workflow selesai.
    """
    events = await service.list_events(
        workflow_id=workflow_id, owner_id=current_user.id
    )
    return WorkflowEventListResponse(items=[_to_event(event) for event in events])


@router.put(
    "/workflows/{workflow_id}/moodle-target",
    response_model=WorkflowResponse,
)
async def update_moodle_target(
    workflow_id: WorkflowIdPath,
    payload: MoodleTargetRequest,
    current_user: User = Depends(instructor_only),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowResponse:
    """Simpan course target Moodle pada workflow (issue BE-11.3).

    ``moodle_course_id`` positif memilih course; ``null`` mengosongkannya.
    Response berbentuk sama dengan ``GET /workflows/{id}``, sehingga client
    tidak perlu membaca ulang setelah menyimpan.
    """
    workflow = await service.set_moodle_course_id(
        workflow_id=workflow_id,
        owner_id=current_user.id,
        moodle_course_id=payload.moodle_course_id,
    )
    return _to_detail(workflow)


@router.websocket("/ws/workflows/{workflow_id}")
async def stream_workflow_events(
    websocket: WebSocket,
    workflow_id: WorkflowIdPath,
    token: str | None = Query(
        default=None,
        description="Access token; browser tidak dapat menyetel header Authorization pada WebSocket.",
    ),
    auth_service: AuthService = Depends(get_auth_service),
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> None:
    """Kirim event workflow secara real-time (design-api §17).

    Handshake ditolak sebelum ``accept`` bila token tidak ada/tidak valid
    (``4401``), peminta bukan dosen (``4403``), atau workflow bukan miliknya
    (``4404``). Setelah terhubung, klien hanya menerima event **baru**; keadaan
    awal dan riwayat tetap diambil lewat HTTP §16 — sesuai kontrak bahwa client
    melakukan initial state fetch sebelum memakai event stream.
    """
    try:
        if not token:
            raise AuthDomainError("websocket tanpa access token")
        user = await auth_service.get_authenticated_user(token)
        _instructor_policy.enforce(user)
        await workflow_service.get_workflow(
            workflow_id=workflow_id, owner_id=user.id
        )
    except AuthorizationError:
        await websocket.close(code=WS_FORBIDDEN)
        return
    except AuthDomainError:
        await websocket.close(code=WS_UNAUTHORIZED)
        return
    except WorkflowDomainError:
        await websocket.close(code=WS_NOT_FOUND)
        return

    queue = workflow_event_broker.subscribe(workflow_id)
    await websocket.accept()
    # Kedua task berjalan bersamaan supaya disconnect client terdeteksi walau
    # workflow sedang tidak menerbitkan event; tanpa itu langganan akan
    # menggantung sampai event berikutnya tiba.
    receive_task = asyncio.create_task(websocket.receive())
    try:
        while True:
            event_task = asyncio.create_task(queue.get())
            done, _ = await asyncio.wait(
                {receive_task, event_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            if receive_task in done:
                message = receive_task.result()
                if message["type"] == "websocket.disconnect":
                    event_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await event_task
                    break
                receive_task = asyncio.create_task(websocket.receive())

            if event_task in done:
                await websocket.send_json(event_task.result())
            else:
                event_task.cancel()
                with suppress(asyncio.CancelledError):
                    await event_task
    except WebSocketDisconnect:
        pass
    finally:
        receive_task.cancel()
        with suppress(asyncio.CancelledError):
            await receive_task
        workflow_event_broker.unsubscribe(workflow_id, queue)
