import { useContext, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { useAction, useApi } from '../../../hooks/useApi';
import { useOnChange } from '../../../hooks/useOnChange';
import { AppStateContext } from '../../../context/appStateContext';
import {
  CONTENT_KIND_LABELS,
  CONTENT_STATUS_META,
  MAX_CONTENT_NOTE_LENGTH,
  REGENERATION_SCOPE,
  VALIDATION_STATUS_META,
  approveContents,
  generateContents,
  getWorkflowContent,
  listContentVersions,
  listWorkflowContents,
  regenerateContents,
  rejectContents,
} from '../../../services/contentService';
import { PLAN_STATUS, getWorkflowPlan } from '../../../services/coursePlanService';
import { Alert, Badge, Card, EmptyState, ErrorAlert, Modal, ProgressBar, Spinner } from '../../../components/ui';
import { approveAndPublish, publishSummary } from '../../../services/publishService';
import { formatExecutionPreconditionError } from '../../../services/executionService';
import InstructionModal from '../../../components/ai/InstructionModal';
import ContentDetailView from '../../../components/ai/course/ContentDetailView';
import {
  approvalBlocker,
  contentGenerationProgressOf,
  groupContentsByWeek,
  isApprovable,
  isContentApproved,
  reviewProgress,
  validationFindings,
} from '../../../utils/contentReview';
import { WORKFLOW_STATUS } from '../../../utils/workflowStatus';
import { formatDateTime } from '../../../utils/format';

const GENERATION_LABELS = {
  [WORKFLOW_STATUS.GENERATING_CONTENT]: 'Agent sedang membuat konten mingguan…',
  [WORKFLOW_STATUS.VALIDATING]: 'Agent sedang memvalidasi konten…',
  [WORKFLOW_STATUS.RETRYING]: 'Agent sedang mencoba ulang pembuatan konten…',
};
// Detail tiap konten dimuat bertahap di latar untuk menghitung temuan validasi, beberapa sekaligus.
const FINDINGS_BATCH = 4;
const meta = (table, key) => table[key] ?? { label: key ?? '-', tone: 'neutral' };

/**
 * Jumlah temuan validasi per konten. GET /contents hanya memberi status dan skor, jadi detail tiap konten
 * (GET /contents/{id}) dimuat di latar setelah daftar tampil. Id konten berbeda tiap versi, sehingga hasilnya
 * disimpan per id selama sesi (satu id = satu versi yang tidak berubah) dan hanya konten baru yang dimuat, juga
 * saat halaman Review dibuka lagi.
 */
const findingCountCache = new Map();

function useFindingCounts(workflowId, items) {
  // Hanya pemicu render ulang setelah sebuah batch selesai; nilainya dibaca dari findingCountCache.
  const [, setLoadedBatches] = useState(0);
  const ids = items.map((item) => item.id).join(',');
  useEffect(() => {
    const pending = (ids ? ids.split(',') : []).filter((id) => !findingCountCache.has(id));
    if (!workflowId || !pending.length) return undefined;
    let cancelled = false;
    (async () => {
      for (let start = 0; start < pending.length && !cancelled; start += FINDINGS_BATCH) {
        const batch = pending.slice(start, start + FINDINGS_BATCH);
        const results = await Promise.all(batch.map((id) => getWorkflowContent(workflowId, id)
          .then((detail) => [id, validationFindings(detail.validation).length])
          .catch(() => [id, null])));
        results.forEach(([id, count]) => count != null && findingCountCache.set(id, count));
        if (cancelled) return;
        setLoadedBatches((n) => n + 1);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workflowId, ids]);
  return Object.fromEntries(items.filter((item) => findingCountCache.has(item.id)).map((item) => [item.id, findingCountCache.get(item.id)]));
}

/** Ringkasan validasi satu konten di daftar: status, skor, dan jumlah temuan. */
function ValidationSummary({ validation, findings }) {
  if (!validation) return <span className="text-xs text-muted">Belum divalidasi</span>;
  const status = meta(VALIDATION_STATUS_META, validation.status);
  return (
    <span className="flex flex-wrap items-center gap-1.5 text-xs">
      <Badge tone={status.tone}>{status.label}</Badge>
      {validation.score != null && <span>Skor {Math.round(validation.score * 100)}%</span>}
      <span className="text-muted">{findings == null ? 'Memuat temuan…' : `${findings} temuan`}</span>
    </span>
  );
}

/** Tombol aksi review untuk satu item konten (dipakai bersama di daftar minggu dan panel detail). */
function ContentActionButtons({ item, generating, approvePending, onRegenerate, onReject, onApprove }) {
  const blocker = approvalBlocker(item);
  return (
    <>
      <button
        type="button"
        className="btn btn--ghost btn--sm"
        disabled={generating}
        onClick={onRegenerate}
      >
        Regenerasi
      </button>
      <button
        type="button"
        className="btn btn--ghost btn--sm"
        disabled={isContentApproved(item)}
        onClick={onReject}
      >
        Tolak
      </button>
      <button
        type="button"
        className="btn btn--primary btn--sm"
        disabled={!!blocker || approvePending}
        title={blocker ?? undefined}
        onClick={onApprove}
      >
        Setujui
      </button>
    </>
  );
}

/** Detail konten terpilih beserta riwayat versinya (GET /contents/{id}/versions); versi lama dapat dibuka. */
function ContentDetailPanel({
  workflowId,
  content,
  generating,
  approvePending,
  onRegenerate,
  onReject,
  onApprove,
  onClose,
}) {
  const [versionId, setVersionId] = useState(content.id);
  const versions = useApi(() => listContentVersions(workflowId, content.id).catch(() => []), [workflowId, content.id]);
  const detail = useApi(() => getWorkflowContent(workflowId, versionId), [workflowId, versionId]);
  const items = [...(versions.data ?? [])].sort((a, b) => b.version - a.version);
  const latestId = items[0]?.id ?? content.id;

  return (
    <Card
      title="Detail konten"
      className="flex flex-col xl:max-h-[calc(100vh-6rem)] max-xl:my-auto max-xl:max-h-[calc(100vh-2rem)] max-xl:w-full max-xl:max-w-2xl max-xl:shadow-xl"
      actions={(
        <>
          <ContentActionButtons
            item={content}
            generating={generating}
            approvePending={approvePending}
            onRegenerate={onRegenerate}
            onReject={onReject}
            onApprove={onApprove}
          />
          <button type="button" className="btn btn--ghost btn--sm" onClick={onClose}>Tutup</button>
        </>
      )}
    >
      <div className="min-h-0 flex-1 overflow-y-auto pr-1">
        {items.length > 1 && (
          <div className="mb-4 flex flex-wrap items-center gap-2 text-sm" role="group" aria-label="Riwayat versi konten">
            <span className="text-muted">Versi:</span>
            {items.map((item) => {
              const active = item.id === versionId;
              const status = meta(CONTENT_STATUS_META, item.status);
              return (
                <button
                  key={item.id}
                  type="button"
                  aria-pressed={active}
                  className={`btn btn--sm ${active ? 'btn--primary' : 'btn--ghost'}`}
                  title={`${status.label}${item.created_at ? ` · ${formatDateTime(item.created_at)}` : ''}`}
                  onClick={() => setVersionId(item.id)}
                >
                  {`Versi ${item.version}`}{item.id === latestId ? ' (terbaru)' : ''}
                </button>
              );
            })}
          </div>
        )}
        {versionId !== latestId && <Alert tone="info" title="Menampilkan versi sebelumnya">Versi lama hanya untuk ditinjau; keputusan review berlaku untuk versi terbaru.</Alert>}
        <ErrorAlert error={detail.error} />
        {detail.loading && !detail.data ? <Spinner label="Memuat konten…" /> : detail.data && <ContentDetailView content={detail.data} />}
      </div>
    </Card>
  );
}

/**
 * Review konten mingguan per workflow (FE-17): daftar per minggu dengan filter jenis dan status, ringkasan validasi,
 * progres review, detail sesuai jenis beserta riwayat versi, serta approve, reject, dan regenerasi per konten,
 * per minggu, atau seluruh konten. Bila belum ada konten dan course plan sudah disetujui, konten dapat digenerate.
 */
export default function CourseReviewPage() {
  const { workflow, workflowId, events = [], refresh } = useCourse();
  const notify = useContext(AppStateContext)?.notify;
  const [kind, setKind] = useState('');
  const [status, setStatus] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  // { type: 'reject' | 'regenerate', scope, weekNumber, contentIds, contentId, label }
  const [dialog, setDialog] = useState(null);
  const [publishOpen, setPublishOpen] = useState(false);
  const navigate = useNavigate();

  const contents = useApi(() => (workflowId ? listWorkflowContents(workflowId) : []), [workflowId]);
  const plan = useApi(() => (workflowId ? getWorkflowPlan(workflowId).catch(() => null) : null), [workflowId]);
  const items = contents.data ?? [];
  const findings = useFindingCounts(workflowId, items);

  // Event workflow (generation per konten/minggu, keputusan review) memuat ulang daftar tanpa memuat ulang halaman.
  const workflowChange = workflow ? `${workflow.status}|${workflow.stage}|${workflow.updated_at}` : null;
  const { reload: reloadContents } = contents;
  useOnChange(workflowChange, () => reloadContents({ silent: true }), 300);

  const afterAction = (message) => {
    notify?.(message, { type: 'success' });
    reloadContents({ silent: true });
    refresh?.();
  };
  const approve = useAction((ids) => approveContents(workflowId, ids), { loadingLabel: 'Menyetujui konten…' });
  const publish = useAction(() => approveAndPublish(workflowId, contents.data ?? []), { loadingLabel: 'Mempublikasikan ke Moodle…' });
  const runPublish = () => publish.run()
    .then(() => {
      setPublishOpen(false);
      notify?.('Konten disetujui dan sedang dikirim ke Moodle.', { type: 'success' });
      refresh?.();
      navigate('../publish', { relative: 'path' });
    })
    .catch(() => {});
  const generate = useAction(() => generateContents(workflowId), { loadingLabel: 'Meminta pembuatan konten…' });
  const runApprove = (ids, message) => approve.run(ids).then(() => afterAction(message)).catch(() => {});

  const progress = reviewProgress(items);
  const summary = publishSummary(items);
  const generating = contentGenerationProgressOf(workflow, events);
  const planApproved = plan.data?.status === PLAN_STATUS.APPROVED;
  const filtered = items.filter((item) => (!kind || item.kind === kind) && (!status || item.status === status));
  const weeks = groupContentsByWeek(filtered);
  const kinds = [...new Set(items.map((item) => item.kind))];
  const approvableIds = (list) => list.filter(isApprovable).map((item) => item.id);
  const allApprovable = approvableIds(items);
  const selected = items.find((item) => item.id === selectedId);

  useEffect(() => {
    if (!selected || dialog) return undefined;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') setSelectedId(null);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [selected, dialog]);

  if (!workflowId) {
    return (
      <Card title="Review konten">
        <EmptyState title="Belum ada workflow untuk kursus ini.">Unggah dan analisis RPS di tab RPS, lalu susun course plan.</EmptyState>
      </Card>
    );
  }
  if (contents.loading && !contents.data) return <Spinner label="Memuat konten…" />;

  return (
    <div className="stack">
      <Card
        title="Review konten mingguan"
        actions={items.length > 0 && (
          <>
            <button
              type="button"
              className="btn btn--ghost"
              disabled={!!generating}
              onClick={() => setDialog({ type: 'regenerate', scope: REGENERATION_SCOPE.COURSE, label: 'seluruh konten' })}
            >
              Regenerasi seluruh konten
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              disabled={!allApprovable.length || approve.pending}
              title={allApprovable.length ? undefined : 'Tidak ada konten lolos validasi yang menunggu persetujuan.'}
              onClick={() => runApprove(allApprovable, `${allApprovable.length} konten disetujui.`)}
            >
              Setujui semua yang lolos validasi ({allApprovable.length})
            </button>
            <button
              type="button"
              className="btn btn--primary"
              disabled={!!generating || !summary.publishable || publish.pending}
              title={summary.publishable ? undefined : 'Belum ada konten yang lolos validasi.'}
              onClick={() => setPublishOpen(true)}
            >
              Setujui &amp; publikasikan ke Moodle
            </button>
          </>
        )}
      >
        <ErrorAlert error={contents.error} />
        <ErrorAlert error={approve.error || generate.error} onClose={() => { approve.clearError(); generate.clearError(); }} />
        {generating && (
          <Alert tone="info" title={GENERATION_LABELS[generating]}>Daftar konten diperbarui otomatis setiap ada konten baru.</Alert>
        )}

        {items.length === 0 ? (
          generating ? null : planApproved ? (
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                className="btn btn--primary"
                disabled={generate.pending}
                onClick={() => generate.run().then(() => afterAction('Pembuatan konten dimulai.')).catch(() => {})}
              >
                {generate.pending ? 'Meminta…' : 'Generate konten'}
              </button>
              <span className="text-sm text-muted">Agent membuat konten setiap minggu sesuai course plan dan konfigurasi aktivitas.</span>
            </div>
          ) : (
            <EmptyState title="Belum ada konten.">
              Konten dibuat setelah course plan disetujui.{' '}
              <Link to="../plan" relative="path">Buka tab Rencana</Link>
            </EmptyState>
          )
        ) : (
          <>
            <ProgressBar completed={progress.approved} total={progress.total} label="Konten disetujui" />
            {progress.complete && (
              <Alert tone="success" title="Seluruh konten telah disetujui">
                <p>
                  Langkah berikutnya: kirim struktur dan seluruh konten ke Moodle.{' '}
                  <Link to="../publish" relative="path" className="font-semibold underline">Lanjut ke Eksekusi Moodle →</Link>
                </p>
              </Alert>
            )}
            <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label="Filter konten">
              <select className="!w-auto" value={kind} onChange={(e) => setKind(e.target.value)} aria-label="Filter jenis konten">
                <option value="">Semua jenis</option>
                {kinds.map((value) => <option key={value} value={value}>{CONTENT_KIND_LABELS[value] ?? value}</option>)}
              </select>
              <select className="!w-auto" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter status konten">
                <option value="">Semua status</option>
                {Object.entries(CONTENT_STATUS_META).map(([value, item]) => <option key={value} value={value}>{item.label}</option>)}
              </select>
            </div>
          </>
        )}
      </Card>

      {items.length > 0 && (
        <div className={`grid gap-4 ${selected ? 'xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] xl:items-start' : ''}`}>
          <div className="stack">
            {weeks.length === 0 && <EmptyState title="Tidak ada konten yang cocok dengan filter." />}
            {weeks.map(({ week, contents: weekItems }) => {
              const weekApprovable = approvableIds(weekItems);
              const weekLabel = week == null ? 'Tanpa minggu' : `Minggu ${week}`;
              return (
                <Card
                  key={week ?? 'none'}
                  title={weekLabel}
                  actions={week != null && (
                    <>
                      <button type="button" className="btn btn--ghost btn--sm" disabled={!!generating} onClick={() => setDialog({ type: 'regenerate', scope: REGENERATION_SCOPE.MINGGU, weekNumber: week, label: weekLabel.toLowerCase() })}>
                        Regenerasi minggu
                      </button>
                      <button type="button" className="btn btn--ghost btn--sm" onClick={() => setDialog({ type: 'reject', contentIds: weekItems.filter((item) => !isContentApproved(item)).map((item) => item.id), label: weekLabel.toLowerCase() })} disabled={weekItems.every(isContentApproved)}>
                        Tolak minggu
                      </button>
                      <button type="button" className="btn btn--secondary btn--sm" disabled={!weekApprovable.length || approve.pending} onClick={() => runApprove(weekApprovable, `${weekApprovable.length} konten ${weekLabel.toLowerCase()} disetujui.`)}>
                        Setujui minggu ({weekApprovable.length})
                      </button>
                    </>
                  )}
                >
                  <ul className="m-0 grid list-none gap-2 p-0" aria-label={`Konten ${weekLabel}`}>
                    {weekItems.map((item) => {
                      const itemStatus = meta(CONTENT_STATUS_META, item.status);
                      return (
                        <li key={item.id} className={`flex flex-wrap items-center gap-3 rounded-md border p-3 ${item.id === selectedId ? 'border-primary bg-primary-light/40' : 'border-line'}`} aria-label={item.title}>
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="text-xs font-semibold text-muted">{CONTENT_KIND_LABELS[item.kind] ?? item.kind}</span>
                              <Badge tone={itemStatus.tone}>{itemStatus.label}</Badge>
                              <span className="text-xs text-muted">Versi {item.version}</span>
                            </div>
                            <button type="button" className="mt-1 block cursor-pointer text-left font-semibold text-primary hover:underline" onClick={() => setSelectedId(item.id)}>
                              {item.title}
                            </button>
                            <div className="mt-1"><ValidationSummary validation={item.validation} findings={findings[item.id]} /></div>
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            <ContentActionButtons
                              item={item}
                              generating={!!generating}
                              approvePending={approve.pending}
                              onRegenerate={() => setDialog({ type: 'regenerate', scope: REGENERATION_SCOPE.ITEM, contentId: item.id, label: `"${item.title}"` })}
                              onReject={() => setDialog({ type: 'reject', contentIds: [item.id], label: `"${item.title}"` })}
                              onApprove={() => runApprove([item.id], `"${item.title}" disetujui.`)}
                            />
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </Card>
              );
            })}
          </div>
          {selected && (
            <div
              data-testid="content-detail-drawer"
              className="xl:sticky xl:top-20 xl:min-w-0 max-xl:fixed max-xl:inset-0 max-xl:z-50 max-xl:flex max-xl:items-start max-xl:justify-end max-xl:overflow-y-auto max-xl:bg-black/40 max-xl:p-4"
              onClick={(event) => {
                if (event.target === event.currentTarget) setSelectedId(null);
              }}
            >
              <ContentDetailPanel
                key={selected.id}
                workflowId={workflowId}
                content={selected}
                generating={!!generating}
                approvePending={approve.pending}
                onRegenerate={() => setDialog({ type: 'regenerate', scope: REGENERATION_SCOPE.ITEM, contentId: selected.id, label: `"${selected.title}"` })}
                onReject={() => setDialog({ type: 'reject', contentIds: [selected.id], label: `"${selected.title}"` })}
                onApprove={() => runApprove([selected.id], `"${selected.title}" disetujui.`)}
                onClose={() => setSelectedId(null)}
              />
            </div>
          )}
        </div>
      )}

      <Modal
        open={publishOpen}
        title="Setujui & publikasikan ke Moodle"
        onClose={() => { setPublishOpen(false); publish.clearError(); }}
        footer={(
          <>
            <button type="button" className="btn btn--ghost" onClick={() => { setPublishOpen(false); publish.clearError(); }}>Batal</button>
            <button type="button" className="btn btn--primary" disabled={publish.pending} onClick={runPublish}>
              {publish.pending ? 'Mempublikasikan…' : 'Ya, publikasikan'}
            </button>
          </>
        )}
      >
        <div className="stack text-sm">
          <p>
            Section mingguan dan <strong>{summary.publishable} konten</strong> akan dikirim ke kursus Moodle
            {summary.toApprove.length > 0 && <> ({summary.toApprove.length} konten disetujui sekarang)</>}.
          </p>
          {summary.skipped.length > 0 && (
            <Alert tone="warning" title={`${summary.skipped.length} konten dilewati`}>
              Konten yang belum lolos validasi atau ditolak tidak dikirim. Regenerasi lalu publikasikan ulang kapan saja.
            </Alert>
          )}
          {publish.error && (
            <Alert tone="danger" title="Publikasi gagal dimulai">{formatExecutionPreconditionError(publish.error)}</Alert>
          )}
        </div>
      </Modal>

      <InstructionModal
        open={dialog?.type === 'reject'}
        title="Tolak konten"
        label="Catatan revisi"
        hint={dialog ? `Konten yang ditolak: ${dialog.label}. Catatan dipakai agent saat regenerasi.` : ''}
        placeholder="Contoh: Contoh kasus kurang relevan dengan materi minggu ini."
        submitLabel="Tolak konten"
        danger
        maxLength={MAX_CONTENT_NOTE_LENGTH}
        onClose={() => setDialog(null)}
        onSubmit={(notes) => rejectContents(workflowId, dialog.contentIds, notes).then(() => afterAction('Konten ditolak.'))}
      />
      <InstructionModal
        open={dialog?.type === 'regenerate'}
        title={dialog?.scope === REGENERATION_SCOPE.COURSE ? 'Regenerasi seluruh konten' : 'Regenerasi konten'}
        label="Catatan revisi"
        hint={dialog?.scope === REGENERATION_SCOPE.COURSE
          ? 'Seluruh konten kursus akan dibuat ulang sebagai versi baru. Pastikan ini yang Anda inginkan; versi lama tetap dapat dibuka.'
          : dialog ? `Hanya ${dialog.label} yang dibuat ulang sebagai versi baru; konten lain tidak berubah.` : ''}
        placeholder="Contoh: Tambahkan contoh kasus sistem informasi kampus."
        submitLabel={dialog?.scope === REGENERATION_SCOPE.COURSE ? 'Ya, regenerasi seluruh konten' : 'Regenerasi'}
        danger={dialog?.scope === REGENERATION_SCOPE.COURSE}
        maxLength={MAX_CONTENT_NOTE_LENGTH}
        onClose={() => setDialog(null)}
        onSubmit={(notes) => regenerateContents(workflowId, { scope: dialog.scope, weekNumber: dialog.weekNumber, contentId: dialog.contentId, notes })
          .then(() => afterAction('Regenerasi konten dimulai.'))}
      />
    </div>
  );
}
