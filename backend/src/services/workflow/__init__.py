"""Workflow Agentic AI: state machine, event, dan orkestrasi (BE-11).

Paket ini memegang state machine workflow beserta riwayat event-nya, dan sejak
BE-11.2 juga orkestrator yang menjalankan tahap pemrosesan + analisis RPS:

- :class:`~src.services.workflow.domain.WorkflowRecord` dan
  :class:`~src.services.workflow.domain.WorkflowEventRecord` — aturan bentuk dan
  lifecycle workflow;
- :class:`~src.services.workflow.service.WorkflowService` — seluruh transisi
  status dan penulisan event (satu tempat untuk aturan audit);
- :class:`~src.services.workflow.repository.WorkflowRepository` — akses tabel
  ``workflows``/``workflow_events``;
- :mod:`src.services.workflow.orchestrator` — urutan tahap
  ``PROCESSING_RPS`` → ``ANALYZING_RPS`` dan entry point background-nya;
- :class:`~src.services.workflow.broker.WorkflowEventBroker` — fan-out event ke
  klien WebSocket (BE-11.3).

Seluruh error domain dipetakan ke HTTP oleh ``src.middlewares``.
"""

from src.services.workflow.broker import WorkflowEventBroker, workflow_event_broker
from src.services.workflow.domain import (
    WorkflowEventRecord,
    WorkflowRecord,
    api_status,
    stage_name,
)
from src.services.workflow.errors import (
    WorkflowDomainError,
    WorkflowNotFoundError,
    WorkflowStateError,
    WorkflowValidationError,
)
from src.services.workflow.orchestrator import (
    RPS_ANALYSIS_STAGES,
    RPS_PROCESSING_STAGES,
    WorkflowStage,
    execute_workflow,
    run_rps_analysis_workflow,
    run_rps_processing_workflow,
)
from src.services.workflow.repository import WorkflowRepository
from src.services.workflow.service import WorkflowService

__all__ = [
    "RPS_ANALYSIS_STAGES",
    "RPS_PROCESSING_STAGES",
    "WorkflowDomainError",
    "WorkflowEventBroker",
    "WorkflowEventRecord",
    "WorkflowNotFoundError",
    "WorkflowRecord",
    "WorkflowRepository",
    "WorkflowService",
    "WorkflowStage",
    "WorkflowStateError",
    "WorkflowValidationError",
    "api_status",
    "execute_workflow",
    "run_rps_analysis_workflow",
    "run_rps_processing_workflow",
    "stage_name",
    "workflow_event_broker",
]
