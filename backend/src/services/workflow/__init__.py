"""Fondasi workflow Agentic AI (BE-11).

Paket ini memegang state machine workflow beserta riwayat event-nya. Isi paket
bertambah per sub-task BE-11:

- BE-11.1 — :class:`~src.services.workflow.domain.WorkflowRecord` dan
  :class:`~src.services.workflow.domain.WorkflowEventRecord` (aturan bentuk dan
  lifecycle), serta :class:`~src.services.workflow.repository.WorkflowRepository`
  sebagai satu-satunya akses tabel ``workflows``/``workflow_events``.
"""
