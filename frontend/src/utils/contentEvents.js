// Event konten dan operasi Moodle per minggu × jenis (BE-19.3, BE-21.1). Payload event tidak membawa metadata, jadi
// minggu, jenis, dan kejadian dibaca dari pesan backend yang formatnya tetap:
// - generation  : "Minggu 3 - Learning Material dimulai|konteksnya disiapkan|sedang dihasilkan|respons model diterima|selesai|diperbaiki|gagal."
// - validasi    : "Minggu 3 - Learning Material selesai|gagal validasi."
// - eksekusi    : "Minggu 3 - Learning Material diterapkan ke Moodle|gagal diterapkan ke Moodle|dilewati."
// - per minggu  : "Minggu 3 selesai: 2 konten berhasil divalidasi, 1 gagal."
import { CONTENT_KIND } from '../services/contentService';
import { WORKFLOW_EVENT, WORKFLOW_STAGE } from './workflowStatus';

const KIND_BY_LABEL = {
  'Learning Material': CONTENT_KIND.LEARNING_MATERIAL,
  'Learning Resource': CONTENT_KIND.RESOURCE,
  Assignment: CONTENT_KIND.ASSIGNMENT,
  Quiz: CONTENT_KIND.QUIZ,
};

/** Keadaan satu konten pada progres generation. */
export const CONTENT_STATE = {
  RUNNING: 'running',
  RETRYING: 'retrying',
  GENERATED: 'generated',
  VALIDATED: 'validated',
  INVALID: 'invalid',
  FAILED: 'failed',
};

export const CONTENT_STATE_META = {
  [CONTENT_STATE.RUNNING]: { label: 'Dibuat', tone: 'info' },
  [CONTENT_STATE.RETRYING]: { label: 'Diperbaiki', tone: 'warning' },
  [CONTENT_STATE.GENERATED]: { label: 'Selesai dibuat', tone: 'info' },
  [CONTENT_STATE.VALIDATED]: { label: 'Lolos validasi', tone: 'success' },
  [CONTENT_STATE.INVALID]: { label: 'Gagal validasi', tone: 'danger' },
  [CONTENT_STATE.FAILED]: { label: 'Gagal', tone: 'danger' },
};

const ITEM_PATTERN = /^Minggu (\d+) - (Learning Material|Learning Resource|Assignment|Quiz) (.+?)\.?$/;
const WEEK_PATTERN = /^Minggu (\d+) selesai: (\d+) konten berhasil divalidasi, (\d+) gagal\.?$/;

/** { week, kind, action } dari pesan event konten/operasi per jenis; null bila pesan bukan format itu. */
export function parseContentMessage(message) {
  const match = ITEM_PATTERN.exec(String(message ?? '').trim());
  return match ? { week: Number(match[1]), kind: KIND_BY_LABEL[match[2]], action: match[3] } : null;
}

const stateOf = (event, action) => {
  if (event.event === WORKFLOW_EVENT.RETRY || action === 'diperbaiki') return CONTENT_STATE.RETRYING;
  if (event.event === WORKFLOW_EVENT.CONTENT_FAILED || action === 'gagal') return CONTENT_STATE.FAILED;
  if (event.event === WORKFLOW_EVENT.CONTENT_VALIDATION_FAILED || action === 'gagal validasi') return CONTENT_STATE.INVALID;
  if (event.event === WORKFLOW_EVENT.CONTENT_VALIDATED) return CONTENT_STATE.VALIDATED;
  if (action === 'selesai') return CONTENT_STATE.GENERATED;
  return CONTENT_STATE.RUNNING;
};

/**
 * Progres generation konten pada run terakhir (sejak WORKFLOW_STAGE_STARTED content_generation terakhir):
 * { weeks: [{ week, items: [{ kind, state }], summary: { validated, failed } | null }], weeksDone, total } atau null bila
 * belum pernah ada generation konten. Keadaan tiap konten mengikuti event terakhirnya.
 */
export function contentGenerationProgress(events = []) {
  const start = events.map((event) => event.event === WORKFLOW_EVENT.STAGE_STARTED && event.stage === WORKFLOW_STAGE.CONTENT_GENERATION).lastIndexOf(true);
  if (start === -1) return null;
  const weeks = new Map();
  const weekOf = (week) => {
    if (!weeks.has(week)) weeks.set(week, { week, items: new Map(), summary: null });
    return weeks.get(week);
  };
  events.slice(start).forEach((event) => {
    const summary = event.event === WORKFLOW_EVENT.WEEK_COMPLETED && WEEK_PATTERN.exec(String(event.message ?? '').trim());
    if (summary) {
      weekOf(Number(summary[1])).summary = { validated: Number(summary[2]), failed: Number(summary[3]) };
      return;
    }
    if (![WORKFLOW_STAGE.CONTENT_GENERATION, WORKFLOW_STAGE.VALIDATION].includes(event.stage)) return;
    const parsed = parseContentMessage(event.message);
    if (!parsed?.kind) return;
    weekOf(parsed.week).items.set(parsed.kind, stateOf(event, parsed.action));
  });
  const list = [...weeks.values()]
    .sort((a, b) => a.week - b.week)
    .map(({ week, items, summary }) => ({ week, items: [...items].map(([kind, state]) => ({ kind, state })), summary }));
  return { weeks: list, weeksDone: list.filter((week) => week.summary).length, total: list.length };
}
