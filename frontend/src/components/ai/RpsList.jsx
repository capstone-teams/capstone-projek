import { useState } from 'react';
import { Link } from 'react-router-dom';
import { EmptyState } from '../ui';
import RpsAnalysisSummary from './RpsAnalysisSummary';
import RpsStatusBadge from './RpsStatusBadge';
import { RPS_STATUS, isRpsInProgress, rpsStatusMeta } from '../../utils/rpsStatus';
import { formatDateTime } from '../../utils/format';

const STAGE_LABELS = { rps_analysis: 'Analisis RPS', document_extraction: 'Konversi dokumen' };

/** Aksi pemulihan: analisis ulang bila dokumen sudah terkonversi, selain itu proses (ulang) dokumen. */
function RecoveryAction({ item, busy, onProcess, onReanalyze }) {
  if (item.status === RPS_STATUS.UPLOADED) {
    return <button type="button" className="btn btn--ghost btn--sm" disabled={busy} onClick={() => onProcess(item)}>{busy ? 'Memulai…' : 'Proses'}</button>;
  }
  if (item.status !== RPS_STATUS.FAILED) return null;
  return item.has_source_document ? (
    <button type="button" className="btn btn--primary btn--sm" disabled={busy} onClick={() => onReanalyze(item)}>{busy ? 'Memulai…' : 'Analisis ulang'}</button>
  ) : (
    <button type="button" className="btn btn--primary btn--sm" disabled={busy} onClick={() => onProcess(item)}>{busy ? 'Memulai…' : 'Proses ulang'}</button>
  );
}

function RpsItem({ item, progress, highlighted, busy, onProcess, onReanalyze, analysisHref, monitorHref }) {
  const [showSummary, setShowSummary] = useState(false);
  const running = isRpsInProgress(item);
  const analyzed = item.status === RPS_STATUS.ANALYZED;
  const step = progress?.progress;
  const analysisLink = analyzed && analysisHref?.(item);
  const monitorLink = item.workflow_id && monitorHref?.(item);

  return (
    <li className={`rounded-lg border border-line p-3 ${highlighted ? 'bg-primary-light' : ''}`}>
      <div className="flex items-start justify-between gap-2 font-semibold">
        <div className="min-w-0">
          <span className="wrap-anywhere">{item.filename}</span>
          {highlighted && <span className="ml-2 text-xs font-normal text-primary">Baru</span>}
        </div>
        <RpsStatusBadge status={item.status} />
      </div>

      {running && (
        <p className="mt-1 text-sm text-muted" aria-live="polite">
          {rpsStatusMeta(item.status).description}
          {progress?.stage && ` Tahap: ${STAGE_LABELS[progress.stage] ?? progress.stage}`}
          {step?.total ? ` (${step.completed}/${step.total})` : ''}
        </p>
      )}
      {item.status === RPS_STATUS.FAILED && (
        <p className="mt-1 text-sm text-danger" role="status">
          {item.processing_error_message ?? progress?.message ?? 'Pemrosesan RPS gagal.'}
        </p>
      )}

      <dl className="mt-2 grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-sm">
        <dt className="text-muted">Diunggah</dt>
        <dd>{formatDateTime(item.created_at)}</dd>
        <dt className="text-muted">Workflow</dt>
        <dd>{item.workflow_id ? <code className="wrap-anywhere">{item.workflow_id}</code> : <span className="muted">Belum dibuat</span>}</dd>
      </dl>

      <div className="mt-2 flex flex-wrap items-center gap-2">
        <RecoveryAction item={item} busy={busy} onProcess={onProcess} onReanalyze={onReanalyze} />
        {analysisLink && <Link to={analysisLink} className="btn btn--ghost btn--sm">Lihat hasil analisis</Link>}
        {analyzed && !analysisLink && (
          <button type="button" className="btn btn--ghost btn--sm" aria-expanded={showSummary} onClick={() => setShowSummary((value) => !value)}>
            {showSummary ? 'Sembunyikan hasil analisis' : 'Lihat hasil analisis'}
          </button>
        )}
        {monitorLink && <Link to={monitorLink} className="btn btn--ghost btn--sm">Pantau workflow</Link>}
      </div>
      {showSummary && <RpsAnalysisSummary rpsId={item.id} />}
    </li>
  );
}

/**
 * Daftar RPS milik dosen dengan status pemrosesan yang diperbarui otomatis.
 * analysisHref/monitorHref (opsional) mengembalikan tujuan tautan bila halamannya dapat dibuka;
 * tanpa analysisHref, hasil analisis ditampilkan ringkas di dalam item.
 */
export default function RpsList({ items, progress = {}, highlightId, busyId, onProcess, onReanalyze, analysisHref, monitorHref }) {
  if (!items.length) {
    return <EmptyState title="Belum ada RPS.">Unggah RPS pertama Anda untuk memulai analisis.</EmptyState>;
  }
  return (
    <ul className="m-0 flex list-none flex-col gap-3 p-0" aria-label="Daftar RPS">
      {items.map((item) => (
        <RpsItem
          key={item.id}
          item={item}
          progress={progress[item.id]}
          highlighted={item.id === highlightId}
          busy={busyId === item.id}
          onProcess={onProcess}
          onReanalyze={onReanalyze}
          analysisHref={analysisHref}
          monitorHref={monitorHref}
        />
      ))}
    </ul>
  );
}
