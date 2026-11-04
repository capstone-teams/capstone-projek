"""Kanal event workflow in-process (BE-11.2).

Endpoint WebSocket (BE-11.3) berlangganan event berdasarkan ``workflow_id``.
Orkestrator menerbitkan event setelah baris ``workflow_events`` berhasil
disimpan, sehingga frame real-time dan riwayat HTTP selalu memuat kejadian yang
sama — klien tidak perlu membedakan dua bentuk payload.

``ponytail:`` broker ini hanya berlaku di dalam satu proses. Beberapa worker
uvicorn atau restart server akan memutus langganan dan event yang terbit di
worker lain tidak terkirim; riwayat HTTP tetap lengkap dan menjadi sumber
kebenaran. Ganti dengan Redis pub/sub bila deployment horizontal membutuhkannya.

Antrean per klien dibatasi: klien lambat kehilangan event real-time (riwayat
HTTP tetap tersedia) alih-alih membuat memori proses tumbuh tanpa batas.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict

__all__ = ["WorkflowEventBroker", "workflow_event_broker"]


class WorkflowEventBroker:
    """Fan-out event ke seluruh pelanggan satu workflow di proses ini."""

    def __init__(self, *, queue_size: int = 100) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._queue_size = queue_size

    def subscribe(self, workflow_id: str) -> asyncio.Queue:
        """Buat antrean pelanggan baru untuk ``workflow_id``."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._queue_size)
        self._subscribers[workflow_id].add(queue)
        return queue

    def unsubscribe(self, workflow_id: str, queue: asyncio.Queue) -> None:
        """Lepas satu antrean; kunci workflow dibuang saat pelanggan terakhir pergi."""
        queues = self._subscribers.get(workflow_id)
        if not queues:
            return
        queues.discard(queue)
        if not queues:
            self._subscribers.pop(workflow_id, None)

    def publish(self, workflow_id: str, payload: dict) -> None:
        """Terbitkan payload ke semua pelanggan; pelanggan lambat dilewati."""
        for queue in tuple(self._subscribers.get(workflow_id, ())):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                # Event ini tetap ada pada riwayat HTTP; jangan menahan
                # orkestrator karena satu klien lambat.
                continue


#: Broker yang dipakai aplikasi. Pengujian dapat menggantinya dengan instance
#: baru agar langganan antar-test tidak saling bocor.
workflow_event_broker = WorkflowEventBroker()
