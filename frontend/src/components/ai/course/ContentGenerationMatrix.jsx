import { useState } from 'react';
import { Link } from 'react-router-dom';
import { MAX_PLAN_NOTE_LENGTH } from '../../../services/coursePlanService';
import {
  CONTENT_KIND,
  CONTENT_KIND_LABELS,
  REGENERATION_SCOPE,
  getWorkflowContent,
  regenerateWorkflowContents,
} from '../../../services/contentService';
import { isExamWeek, weekTypeLabel } from '../../../utils/coursePlan';
import {
  CONTENT_CELL_STATUS,
  WORKFLOW_STATUS,
  deriveContentMatrixRows,
  isWorkflowBusy,
  workflowStatusOf,
} from '../../../utils/workflowStatus';
import { Alert, Badge, Card, ErrorAlert, Modal, Spinner } from '../../ui';
import InstructionModal from '../InstructionModal';

const MATRIX_COLUMNS = [
  CONTENT_KIND.LEARNING_MATERIAL,
  CONTENT_KIND.RESOURCE,
  CONTENT_KIND.ASSIGNMENT,
  CONTENT_KIND.QUIZ,
];

function extractContentErrors(detail) {
  if (!detail) return [];
  const messages = [];
  const validationErrors = detail.validation?.errors;
  if (validationErrors && typeof validationErrors === 'object') {
    Object.values(validationErrors).forEach((entry) => {
      if (Array.isArray(entry)) {
        entry.forEach((msg) => {
          if (msg) messages.push(String(msg));
        });
      } else if (entry) {
        messages.push(String(entry));
      }
    });
  }
  const dataError = detail.content_data?.error;
  if (dataError?.message) messages.push(String(dataError.message));
  if (Array.isArray(dataError?.details)) {
    dataError.details.forEach((msg) => {
      if (msg) messages.push(String(msg));
    });
  }
  return [...new Set(messages)];
}

function fallbackPlanFromContents(contents = []) {
  const weeks = [...new Set(contents.map((item) => item?.week_number).filter((n) => Number.isInteger(n) && n > 0))]
    .sort((a, b) => a - b)
    .map((weekNumber) => ({
      week_number: weekNumber,
      title: `Minggu ${weekNumber}`,
      week_type: 'regular',
    }));
  return { weeks };
}

function MatrixCell({ cell, week, busy, onInspectError, onRegenerate }) {
  const kindLabel = CONTENT_KIND_LABELS[cell.kind] ?? cell.kind;
  const record = cell.record;

  switch (cell.status) {
    case CONTENT_CELL_STATUS.SKIPPED:
      return (
        <span
          className="text-xs text-muted"
          title={cell.reason === 'week_type' ? `${kindLabel} tidak berlaku untuk tipe minggu ini` : `${kindLabel} tidak dijadwalkan`}
        >
          -
        </span>
      );
    case CONTENT_CELL_STATUS.PENDING:
      return <Badge tone="neutral">Menunggu</Badge>;
    case CONTENT_CELL_STATUS.PROCESSING:
      return <Badge tone="info">Diproses</Badge>;
    case CONTENT_CELL_STATUS.RETRYING:
      return <Badge tone="warning">↻ Retry/Fix</Badge>;
    case CONTENT_CELL_STATUS.COMPLETED:
      return (
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge tone="success">✓ Selesai</Badge>
          {record?.version != null && (
            <span className="text-xs text-muted">v{record.version}</span>
          )}
        </div>
      );
    case CONTENT_CELL_STATUS.FAILED:
      return (
        <div className="flex flex-col items-start gap-1.5">
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge tone="danger">✕ Gagal</Badge>
            {record?.validation?.retry_count > 0 && (
              <span className="text-[11px] text-muted">
                ({record.validation.retry_count}x retry)
              </span>
            )}
          </div>
          {record?.id && (
            <div className="flex flex-wrap gap-1.5">
              <button
                type="button"
                className="btn btn--ghost !min-h-0 !px-2 !py-1 !text-xs"
                aria-label={`Lihat error Minggu ${week.week_number} ${kindLabel}`}
                onClick={() => onInspectError(record, week)}
              >
                Lihat error
              </button>
              <button
                type="button"
                className="btn btn--secondary !min-h-0 !px-2 !py-1 !text-xs"
                disabled={busy}
                aria-label={`Regenerasi Minggu ${week.week_number} ${kindLabel}`}
                onClick={() => onRegenerate(record, week)}
              >
                Regenerasi
              </button>
            </div>
          )}
        </div>
      );
    default:
      return <Badge tone="neutral">-</Badge>;
  }
}

/**
 * Matriks progres generation konten (FE-16.2):
 * - Baris = seluruh minggu course plan (termasuk UTS/UAS berstatus "Ujian / Tidak berlaku");
 * - Kolom = 4 jenis konten (Learning Material, Learning Resource, Assignment, Quiz);
 * - Pembaruan otomatis dari data awal GET .../contents dan event AKTIVITAS_AGENT / RETRY_FIX (FE-10.2);
 * - Ringkasan jumlah selesai & gagal, tautan ke halaman Review saat WAITING_FOR_REVIEW, modal detail error
 *   untuk sel Gagal, serta aksi regenerasi ITEM.
 */
export default function ContentGenerationMatrix({
  workflowId,
  workflow,
  events = [],
  plan,
  contents = [],
  contentsLoading = false,
  contentsError = null,
  onRetryContents,
  onRegenerated,
}) {
  const [errorModal, setErrorModal] = useState(null); // { record, week, loading, error, detail }
  const [regenTarget, setRegenTarget] = useState(null); // { record, week }
  const [regenNotice, setRegenNotice] = useState(null);

  const effectivePlan = plan?.weeks?.length ? plan : fallbackPlanFromContents(contents);
  const rows = deriveContentMatrixRows(effectivePlan, contents, events, workflow);
  const busy = isWorkflowBusy(workflow);
  const waitingForReview = workflowStatusOf(workflow) === WORKFLOW_STATUS.WAITING_FOR_REVIEW;

  let completedCount = 0;
  let failedCount = 0;
  let activeCount = 0;

  rows.forEach(({ exam, cells }) => {
    if (exam) return;
    MATRIX_COLUMNS.forEach((kind) => {
      const status = cells[kind]?.status;
      if (status === CONTENT_CELL_STATUS.COMPLETED) completedCount += 1;
      else if (status === CONTENT_CELL_STATUS.FAILED) failedCount += 1;
      else if (status === CONTENT_CELL_STATUS.PROCESSING || status === CONTENT_CELL_STATUS.RETRYING) activeCount += 1;
    });
  });

  const openErrorModal = async (record, week) => {
    const requestId = record.id;
    setErrorModal({ record, week, loading: true, error: null, detail: null });
    try {
      const detail = await getWorkflowContent(workflowId, record.id);
      setErrorModal((current) => (
        current?.record?.id === requestId
          ? { record, week, loading: false, error: null, detail }
          : current
      ));
    } catch (error) {
      setErrorModal((current) => (
        current?.record?.id === requestId
          ? { record, week, loading: false, error, detail: null }
          : current
      ));
    }
  };

  const errorMessages = extractContentErrors(errorModal?.detail);
  const errorKindLabel = errorModal ? (CONTENT_KIND_LABELS[errorModal.record.kind] ?? errorModal.record.kind) : '';
  const regenKindLabel = regenTarget ? (CONTENT_KIND_LABELS[regenTarget.record.kind] ?? regenTarget.record.kind) : '';

  return (
    <Card
      title="Progres Generation Konten"
      actions={(
        <div className="flex flex-wrap items-center gap-2" aria-label="Ringkasan status konten">
          <Badge tone="success">{completedCount} selesai</Badge>
          <Badge tone={failedCount > 0 ? 'danger' : 'neutral'}>{failedCount} gagal</Badge>
          {activeCount > 0 && <Badge tone="info">{activeCount} diproses</Badge>}
        </div>
      )}
    >
      <div className="stack">
        {contentsError && (
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="min-w-0 flex-1">
              <ErrorAlert error={contentsError} />
            </div>
            {onRetryContents && (
              <button type="button" className="btn btn--ghost btn--sm" onClick={onRetryContents}>
                Coba lagi
              </button>
            )}
          </div>
        )}

        {regenNotice && (
          <Alert tone="info" onClose={() => setRegenNotice(null)}>
            {regenNotice}
          </Alert>
        )}

        {waitingForReview && (completedCount > 0 || failedCount > 0) && (
          <Alert
            tone={failedCount > 0 ? 'warning' : 'success'}
            title={failedCount > 0 ? 'Generation selesai sebagian — perlu perhatian' : 'Generation konten selesai'}
          >
            <p>
              {failedCount > 0
                ? `${completedCount} konten berhasil dibuat dan ${failedCount} gagal. Anda dapat meregenerasi item yang gagal atau meninjau konten yang sudah jadi.`
                : `Seluruh ${completedCount} konten siap ditinjau pada halaman Review sebelum diterapkan ke Moodle.`}
            </p>
            <Link to="../review" relative="path" className="btn btn--primary btn--sm mt-2">
              Buka Halaman Review →
            </Link>
          </Alert>
        )}

        {contentsLoading && rows.length === 0 ? (
          <Spinner label="Memuat matriks progres konten…" />
        ) : rows.length === 0 ? (
          <p className="text-sm text-muted">Belum ada data minggu atau konten yang diproses.</p>
        ) : (
          <div className="table-wrap rounded-lg border border-line" role="region" aria-label="Matriks progres konten mingguan" tabIndex={0}>
            <table className="table">
              <thead>
                <tr>
                  <th scope="col" className="min-w-[200px]">Minggu</th>
                  {MATRIX_COLUMNS.map((kind) => (
                    <th key={kind} scope="col" className="min-w-[140px]">
                      {CONTENT_KIND_LABELS[kind]}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map(({ week, exam, cells }) => {
                  const typeLabel = weekTypeLabel(week);
                  const examWeek = exam || isExamWeek(week);
                  return (
                    <tr key={week.week_number} className={examWeek ? 'bg-surface/60' : undefined}>
                      <th scope="row" className="text-left font-medium">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="font-semibold text-ink">Minggu {week.week_number}</span>
                          {typeLabel && (
                            <Badge tone={examWeek ? 'neutral' : 'info'}>{typeLabel}</Badge>
                          )}
                        </div>
                        {week.title && (
                          <div className="mt-0.5 max-w-[220px] truncate text-xs font-normal text-muted" title={week.title}>
                            {week.title}
                          </div>
                        )}
                      </th>
                      {examWeek ? (
                        <td colSpan={MATRIX_COLUMNS.length} className="text-center text-xs text-muted">
                          Ujian / Tidak berlaku
                        </td>
                      ) : (
                        MATRIX_COLUMNS.map((kind) => (
                          <td key={kind}>
                            <MatrixCell
                              cell={cells[kind]}
                              week={week}
                              busy={busy}
                              onInspectError={(record, wk) => openErrorModal(record, wk)}
                              onRegenerate={(record, wk) => setRegenTarget({ record, week: wk })}
                            />
                          </td>
                        ))
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal Detail Error Item Gagal */}
      <Modal
        open={Boolean(errorModal)}
        title={errorModal ? `Detail Kegagalan — Minggu ${errorModal.week.week_number} (${errorKindLabel})` : ''}
        onClose={() => setErrorModal(null)}
      >
        {errorModal && (
          <div className="stack">
            {errorModal.loading && <Spinner label="Memuat detail kegagalan…" />}
            <ErrorAlert error={errorModal.error} />
            {!errorModal.loading && !errorModal.error && (
              <>
                <p className="text-sm text-muted">
                  Versi {errorModal.detail?.version ?? errorModal.record.version ?? 1}
                  {errorModal.detail?.validation?.retry_count > 0 && ` · Dicoba ulang ${errorModal.detail.validation.retry_count} kali`}
                </p>
                {errorMessages.length > 0 ? (
                  <Alert tone="danger" title="Penyebab kegagalan">
                    <ul className="m-0 list-disc space-y-1 pl-4 text-sm">
                      {errorMessages.map((msg, index) => (
                        <li key={index}>{msg}</li>
                      ))}
                    </ul>
                  </Alert>
                ) : (
                  <Alert tone="danger" title="Konten gagal divalidasi">
                    Tidak ada rincian pesan error tambahan dari server.
                  </Alert>
                )}
              </>
            )}
            <div className="form__actions">
              <button type="button" className="btn btn--ghost" onClick={() => setErrorModal(null)}>
                Tutup
              </button>
              <button
                type="button"
                className="btn btn--primary"
                disabled={busy}
                onClick={() => {
                  const target = { record: errorModal.record, week: errorModal.week };
                  setErrorModal(null);
                  setRegenTarget(target);
                }}
              >
                Regenerasi item ini
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Modal Catatan Revisi untuk Regenerasi Scope ITEM */}
      <InstructionModal
        key={regenTarget?.record?.id ?? 'closed'}
        open={Boolean(regenTarget)}
        title={regenTarget ? `Regenerasi Minggu ${regenTarget.week.week_number} — ${regenKindLabel}` : ''}
        label="Catatan revisi"
        hint="Catatan revisi wajib diisi agar agent memperbaiki bagian yang bermasalah."
        placeholder="Contoh: Pastikan kode Sub-CPMK sesuai rencana minggu ini dan perbaiki tautan referensi."
        submitLabel="Mulai Regenerasi"
        maxLength={MAX_PLAN_NOTE_LENGTH}
        onClose={() => setRegenTarget(null)}
        onSubmit={(notes) => regenerateWorkflowContents(workflowId, {
          scope: REGENERATION_SCOPE.ITEM,
          content_id: regenTarget.record.id,
          notes,
        }).then((res) => {
          setRegenNotice(res?.message || 'Regenerasi item dijadwalkan.');
          return onRegenerated?.(res);
        })}
      />
    </Card>
  );
}
