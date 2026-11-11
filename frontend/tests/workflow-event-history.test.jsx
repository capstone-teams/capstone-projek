import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import WorkflowDetail from '../src/components/ai/WorkflowDetail';
import WorkflowEventTimeline from '../src/components/ai/WorkflowEventTimeline';
import * as workflowService from '../src/services/workflowService';
import { EVENT_TYPE, MAX_WORKFLOW_EVENTS, countEventTypes, eventTimeline, mergeEvents } from '../src/utils/workflowStatus';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

let second = 0;
const ev = (event, stage, message, extra = {}) => ({
  event, workflow_id: 'wf1', stage, progress: { completed: 0, total: 2 }, message,
  timestamp: new Date(Date.UTC(2026, 10, 2, 9, 0, second++)).toISOString(), ...extra,
});

// Bentuk riwayat nyata dari backend: proses pertama gagal di analisis, lalu dianalisis ulang dengan retry.
function history() {
  second = 0;
  return [
    ev('WORKFLOW_STARTED', null, 'Workflow dimulai.'),
    ev('WORKFLOW_STAGE_STARTED', 'rps_processing', 'Tahap pemrosesan RPS dimulai.'),
    ev('WORKFLOW_STAGE_COMPLETED', 'rps_processing', 'Tahap pemrosesan RPS selesai.'),
    ev('WORKFLOW_STAGE_STARTED', 'rps_analysis', 'Tahap analisis RPS dimulai.'),
    ev('WORKFLOW_STAGE_PROGRESS', 'rps_analysis', 'Mengirim RPS ke model (percobaan 1/3)'),
    ev('WORKFLOW_FAILED', 'rps_analysis', 'Terjadi kesalahan pada layanan model.'),
    ev('WORKFLOW_STARTED', null, 'Workflow dimulai.'),
    ev('WORKFLOW_STAGE_STARTED', 'rps_analysis', 'Tahap analisis RPS dimulai.'),
    ev('WORKFLOW_RETRY', 'rps_analysis', 'Output tidak valid. Memperbaiki (percobaan 2/3).'),
    ev('WORKFLOW_STAGE_COMPLETED', 'rps_analysis', 'Analisis RPS selesai.'),
    ev('WORKFLOW_COMPLETED', 'rps_analysis', 'Workflow selesai.'),
  ];
}

describe('FE-10.3 data timeline', () => {
  it('memberi kategori dan nomor proses pada setiap event', () => {
    const timeline = eventTimeline(history());
    expect(timeline.map((e) => e.run)).toEqual([1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2]);
    expect(timeline.find((e) => e.event === 'WORKFLOW_FAILED').type).toBe(EVENT_TYPE.ERROR_FAILURE);
    expect(timeline.find((e) => e.event === 'WORKFLOW_RETRY').type).toBe(EVENT_TYPE.RETRY_FIX);
    expect(timeline.find((e) => e.event === 'WORKFLOW_STAGE_PROGRESS').type).toBe(EVENT_TYPE.AKTIVITAS_AGENT);
    // 2 WORKFLOW_STARTED + 3 STAGE_STARTED + 2 STAGE_COMPLETED + 1 WORKFLOW_COMPLETED.
    expect(countEventTypes(timeline)).toEqual({ PERUBAHAN_TAHAP: 8, AKTIVITAS_AGENT: 1, ERROR_FAILURE: 1, RETRY_FIX: 1 });
  });

  it('riwayat tanpa WORKFLOW_STARTED di awal tetap dimulai dari proses 1', () => {
    expect(eventTimeline([ev('WORKFLOW_STAGE_STARTED', 'rps_analysis', 'x')])[0].run).toBe(1);
    expect(eventTimeline([])).toEqual([]);
  });

  it('batas penyimpanan cukup besar untuk riwayat panjang', () => {
    second = 0;
    const many = Array.from({ length: 700 }, (_, i) => ev('WORKFLOW_STAGE_PROGRESS', 'content_generation', `m${i}`));
    expect(MAX_WORKFLOW_EVENTS).toBeGreaterThanOrEqual(2000);
    expect(mergeEvents([], many)).toHaveLength(700);
  });
});

describe('FE-10.3 tampilan timeline', () => {
  let container;
  let root;
  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });
  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.restoreAllMocks();
  });
  const render = (node) => act(async () => root.render(node));
  const items = () => [...container.querySelectorAll('ol[aria-label="Riwayat event workflow"] > li')];
  const filter = (label) => [...container.querySelectorAll('[aria-label="Filter jenis event"] button')].find((b) => b.textContent.startsWith(label));

  it('menampilkan seluruh event dari yang terbaru di atas dengan jenis, tahap, pesan, dan waktu', async () => {
    const events = history();
    await render(<WorkflowEventTimeline events={events} />);
    expect(items()).toHaveLength(events.length);
    expect(items().map((li) => li.dataset.event)).toEqual(events.map((e) => e.event).reverse());
    const failed = items()[events.length - 1 - 5];
    expect(failed.textContent).toContain('Kegagalan'); // jenis event
    expect(failed.textContent).toContain('Workflow gagal'); // nama event
    expect(failed.textContent).toContain('Analisis RPS'); // tahap
    expect(failed.textContent).toContain('Terjadi kesalahan pada layanan model.'); // pesan
    expect(failed.querySelector('time').getAttribute('dateTime')).toBe(events[5].timestamp); // waktu
    expect(failed.querySelector('time').textContent).toMatch(/\d{2}[.:]\d{2}[.:]\d{2}/);
  });

  it('menandai ERROR_FAILURE dan RETRY_FIX secara visual dengan warna dan bentuk berbeda', async () => {
    await render(<WorkflowEventTimeline events={history()} />);
    const failure = container.querySelector('[data-event-type="ERROR_FAILURE"]');
    const retry = container.querySelector('[data-event-type="RETRY_FIX"]');
    const plain = container.querySelector('[data-event-type="PERUBAHAN_TAHAP"]');
    expect(failure.textContent).toContain('✕');
    expect(retry.textContent).toContain('↻');
    expect(failure.querySelector('.bg-danger-light')).not.toBeNull();
    expect(retry.querySelector('.bg-warning-light')).not.toBeNull();
    expect(plain.querySelector('.bg-danger-light, .bg-warning-light')).toBeNull();
    expect(retry.textContent).toContain('Percobaan ulang');
  });

  it('menyaring event berdasarkan jenisnya, dengan jumlah per jenis', async () => {
    await render(<WorkflowEventTimeline events={history()} />);
    expect(filter('Semua').textContent).toBe('Semua (11)');
    expect(filter('Semua').getAttribute('aria-pressed')).toBe('true');
    expect(filter('Kegagalan').textContent).toBe('Kegagalan (1)');
    expect(filter('Operasi kursus')).toBeUndefined(); // jenis tanpa event tidak ditawarkan

    await act(async () => filter('Kegagalan').click());
    expect(items().map((li) => li.dataset.eventType)).toEqual(['ERROR_FAILURE']);
    expect(filter('Kegagalan').getAttribute('aria-pressed')).toBe('true');

    await act(async () => filter('Percobaan ulang').click());
    expect(items().map((li) => li.dataset.event)).toEqual(['WORKFLOW_RETRY']);

    await act(async () => filter('Semua').click());
    expect(items()).toHaveLength(11);
  });

  it('menandai awal tiap proses bila workflow dijalankan ulang, hanya saat tanpa filter', async () => {
    await render(<WorkflowEventTimeline events={history()} />);
    expect(container.textContent).toContain('Proses ke-1');
    expect(container.textContent).toContain('Proses ke-2');
    // Proses terbaru tampil lebih dulu.
    expect(container.textContent.indexOf('Proses ke-2')).toBeLessThan(container.textContent.indexOf('Proses ke-1'));
    await act(async () => filter('Perubahan tahap').click());
    expect(container.textContent).not.toContain('Proses ke-');
  });

  it('workflow sekali jalan tanpa penanda proses, dan riwayat kosong menampilkan keadaan kosong', async () => {
    await render(<WorkflowEventTimeline events={history().slice(6)} />);
    expect(container.textContent).not.toContain('Proses ke-');
    await render(<WorkflowEventTimeline events={[]} />);
    expect(container.textContent).toContain('Belum ada event.');
    expect(container.querySelector('[aria-label="Filter jenis event"]')).toBeNull();
  });

  it.each([
    ['COMPLETED', 'WORKFLOW_COMPLETED'],
    ['FAILED', 'WORKFLOW_FAILED'],
  ])('riwayat lengkap tampil di detail workflow yang %s (lebih dari 30 event)', async (status, last) => {
    second = 0;
    const events = [
      ev('WORKFLOW_STARTED', null, 'Workflow dimulai.'),
      ...Array.from({ length: 40 }, (_, i) => ev('WORKFLOW_STAGE_PROGRESS', 'rps_analysis', `Langkah ${i + 1}`)),
      ev(last, 'rps_analysis', 'Selesai.'),
    ];
    vi.spyOn(workflowService, 'getWorkflow').mockResolvedValue({
      id: 'wf1', status, stage: null, progress: { completed: 2, total: 2 }, rps_id: 'rps1',
      created_at: events[0].timestamp, updated_at: events.at(-1).timestamp, moodle_course_id: null,
    });
    vi.spyOn(workflowService, 'getWorkflowEvents').mockResolvedValue(events);
    await render(<WorkflowDetail workflowId="wf1" rpsName="RPS Uji" />);
    for (let i = 0; i < 50 && !items().length; i += 1) await act(() => new Promise((resolve) => setTimeout(resolve, 20)));
    expect(items()).toHaveLength(42);
    // Terbaru di atas.
    expect(items()[0].dataset.event).toBe(last);
    expect(items().at(-1).dataset.event).toBe('WORKFLOW_STARTED');
  });
});
