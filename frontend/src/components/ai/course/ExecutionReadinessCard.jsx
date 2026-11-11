import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert, Badge, Card, ErrorAlert, Spinner } from '../../ui';
import ExecutionConfirmModal from './ExecutionConfirmModal';
import { CONTENT_KIND_LABELS, CONTENT_STATUS_META } from '../../../services/contentService';
import {
  EXECUTION_SCOPE,
  formatExecutionPreconditionError,
  startExecution,
} from '../../../services/executionService';
import { bindWorkflowToCourse } from '../../../services/workflowService';
import { PLAN_STATUS } from '../../../services/coursePlanService';
import { evaluateContentApprovalReadiness } from '../../../utils/executionReadiness';

const MAX_UNAPPROVED_PREVIEW = 6;

/**
 * Kartu pemeriksaan kesiapan eksekusi Moodle (FE-13.1 & FE-18.1).
 * Mendukung cakupan STRUCTURE (3 prasyarat) dan FULL (4 prasyarat termasuk approval
 * seluruh konten jenis aktif), tautan perbaikan cepat, serta dialog konfirmasi.
 */
export default function ExecutionReadinessCard({
  workflowId,
  workflow,
  courseTarget,
  plan,
  planLoading = false,
  moodleStatus,
  moodleStatusLoading = false,
  contents = [],
  contentsLoading = false,
  instructorSetup = null,
  onExecutionStarted,
}) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState(null);
  const [scopeOverride, setScopeOverride] = useState(null);

  const readiness = evaluateContentApprovalReadiness(contents, instructorSetup);
  const selectedScope = scopeOverride?.workflowId === workflowId
    ? scopeOverride.scope
    : (readiness.hasAnyContent ? EXECUTION_SCOPE.FULL : EXECUTION_SCOPE.STRUCTURE);
  const isFull = selectedScope === EXECUTION_SCOPE.FULL;

  const selectScope = (scope) => {
    setError(null);
    setScopeOverride({ workflowId, scope });
  };

  // 1. Prasyarat: Course Plan disetujui (APPROVED)
  const isPlanApproved = plan?.status === PLAN_STATUS.APPROVED;
  const planStatusLabel = plan?.status === PLAN_STATUS.APPROVED
    ? `Disetujui (Versi ${plan.version ?? 1})`
    : plan?.status === PLAN_STATUS.DRAFT
    ? 'Draft (Menunggu Persetujuan)'
    : plan?.status
    ? String(plan.status)
    : 'Belum Dibuat';

  // 2. Prasyarat: Target kursus Moodle tersimpan
  const targetId = workflow?.moodle_course_id || courseTarget?.moodle_course_id || courseTarget?.id;
  const isTargetSet = Boolean(targetId);
  const targetName = courseTarget?.fullname || courseTarget?.name || (targetId ? `Kursus #${targetId}` : null);

  // 3. Prasyarat: Koneksi server Moodle
  const isMoodleConnected = Boolean(moodleStatus?.connected || moodleStatus?.status === 'CONNECTED');

  // 4. Prasyarat tambahan FULL: seluruh konten jenis aktif berstatus APPROVED / EXECUTED
  const isContentsReady = !isFull || (readiness.hasActiveContents && readiness.allApproved);

  // Kesiapan agregat
  const allReady = Boolean(isPlanApproved && isTargetSet && isMoodleConnected && isContentsReady && workflowId);
  const weekCount = plan?.weeks?.length || 16;

  const handleStart = async () => {
    if (!allReady || executing) return;
    setExecuting(true);
    setError(null);
    try {
      const numericTarget = Number(targetId);
      if (
        Number.isInteger(numericTarget)
        && numericTarget > 0
        && Number(workflow?.moodle_course_id) !== numericTarget
      ) {
        await bindWorkflowToCourse(workflowId, numericTarget, {
          rpsId: workflow?.rps_id,
          throwOnError: true,
        });
      }
      const response = await startExecution(workflowId, selectedScope);
      setConfirmOpen(false);
      onExecutionStarted?.(response);
    } catch (err) {
      setConfirmOpen(false);
      setError(formatExecutionPreconditionError(err));
    } finally {
      setExecuting(false);
    }
  };

  const unapprovedPreview = readiness.unapprovedItems.slice(0, MAX_UNAPPROVED_PREVIEW);
  const remainingUnapproved = readiness.unapprovedItems.length - unapprovedPreview.length;

  return (
    <Card
      title={isFull ? 'Kesiapan Eksekusi Course ke Moodle (FULL)' : 'Kesiapan Eksekusi Struktur Course'}
      actions={(
        <div className="inline-flex flex-wrap rounded-lg border border-line bg-surface-subtle p-0.5" role="tablist" aria-label="Mode eksekusi Moodle">
          <button
            type="button"
            role="tab"
            aria-selected={!isFull}
            className={`btn btn--xs ${!isFull ? 'btn--primary' : 'btn--ghost'}`}
            onClick={() => selectScope(EXECUTION_SCOPE.STRUCTURE)}
          >
            Struktur Saja
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={isFull}
            className={`btn btn--xs ${isFull ? 'btn--primary' : 'btn--ghost'}`}
            onClick={() => selectScope(EXECUTION_SCOPE.FULL)}
          >
            <span>Lengkap: Struktur + Konten</span>
            {readiness.hasAnyContent && (
              <span className={`ml-1 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                isFull ? 'bg-white/20 text-white' : 'bg-primary/10 text-primary'
              }`}>
                Disarankan
              </span>
            )}
          </button>
        </div>
      )}
    >
      <p className="text-sm text-muted mb-3">
        {isFull
          ? 'Mode Lengkap otomatis membuat atau memperbarui 16 section mingguan sekaligus seluruh materi, sumber belajar, tugas, dan kuis yang disetujui — Anda tidak perlu menjalankan "Struktur Saja" secara terpisah.'
          : 'Mode Struktur Saja hanya membuat atau memperbarui kerangka 16 section mingguan tanpa menerbitkan materi, tugas, atau kuis. Gunakan mode ini bila Anda baru menyetujui Rencana dan belum ingin menerbitkan konten.'}
      </p>

      {!isFull && readiness.hasActiveContents && (
        <div className="mb-4">
          <Alert tone="info" title="Konten pembelajaran sudah tersedia">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
              <span>
                {readiness.allApproved
                  ? `Seluruh ${readiness.approvedCount} konten aktif sudah disetujui dan siap diterbitkan. Untuk menerbitkan konten sekaligus mengaktifkan tahap Verifikasi (Step 6), gunakan mode Lengkap: Struktur + Konten.`
                  : 'Alur kerja sudah memiliki konten aktif. Untuk menerbitkan seluruh konten sekaligus memverifikasi hasil akhir di Step 6, pilih mode Lengkap setelah seluruh konten disetujui.'}
              </span>
              <button
                type="button"
                className="btn btn--secondary btn--xs"
                onClick={() => selectScope(EXECUTION_SCOPE.FULL)}
              >
                Pindah ke Mode Lengkap →
              </button>
            </div>
          </Alert>
        </div>
      )}

      {error && (
        <div className="mb-4">
          <ErrorAlert error={error} onClose={() => setError(null)} />
        </div>
      )}

      {/* Daftar Checklist Prasyarat */}
      <div className="divide-y divide-line rounded-lg border border-line bg-surface mb-5">
        {/* Item 1: Course Plan */}
        <div className="flex flex-wrap items-center justify-between gap-3 p-3.5">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold ${
                isPlanApproved ? 'bg-success text-white' : 'bg-muted/20 text-muted'
              }`}>
                {isPlanApproved ? '✓' : '1'}
              </span>
              <span className="font-semibold text-sm">Course Plan Disetujui</span>
            </div>
            <p className="mt-1 text-xs text-muted pl-7">
              {isPlanApproved
                ? 'Rencana mingguan telah disetujui oleh dosen pengampu.'
                : 'Rencana pembelajaran harus disetujui terlebih dahulu sebelum eksekusi ke Moodle.'}
            </p>
          </div>
          <div className="flex items-center gap-2 pl-7 sm:pl-0">
            {planLoading ? (
              <Spinner size="sm" />
            ) : isPlanApproved ? (
              <Badge tone="success">{planStatusLabel}</Badge>
            ) : (
              <>
                <Badge tone="warning">{planStatusLabel}</Badge>
                <Link
                  to="../plan"
                  relative="path"
                  className="btn btn--secondary btn--xs"
                >
                  Buka Tab Rencana →
                </Link>
              </>
            )}
          </div>
        </div>

        {/* Item 2: Target Kursus Moodle */}
        <div className="flex flex-wrap items-center justify-between gap-3 p-3.5">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold ${
                isTargetSet ? 'bg-success text-white' : 'bg-muted/20 text-muted'
              }`}>
                {isTargetSet ? '✓' : '2'}
              </span>
              <span className="font-semibold text-sm">Target Kursus Moodle</span>
            </div>
            <p className="mt-1 text-xs text-muted pl-7">
              {isTargetSet
                ? `Terhubung ke: ${targetName} (#${targetId})`
                : 'Mata kuliah target di Moodle belum ditentukan untuk alur kerja ini.'}
            </p>
          </div>
          <div className="flex items-center gap-2 pl-7 sm:pl-0">
            {isTargetSet ? (
              <Badge tone="success">Terhubung (#{targetId})</Badge>
            ) : (
              <>
                <Badge tone="danger">Belum Dipilih</Badge>
                <Link
                  to="../target"
                  relative="path"
                  className="btn btn--secondary btn--xs"
                >
                  Pilih Target Kursus →
                </Link>
              </>
            )}
          </div>
        </div>

        {/* Item 3: Status Koneksi Moodle */}
        <div className="flex flex-wrap items-center justify-between gap-3 p-3.5">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold ${
                isMoodleConnected ? 'bg-success text-white' : 'bg-muted/20 text-muted'
              }`}>
                {isMoodleConnected ? '✓' : '3'}
              </span>
              <span className="font-semibold text-sm">Koneksi Server Moodle</span>
            </div>
            <p className="mt-1 text-xs text-muted pl-7">
              {isMoodleConnected
                ? `Koneksi Web Service aktif (${moodleStatus?.release || moodleStatus?.site_name || 'Moodle API'}).`
                : (moodleStatus?.message || 'Server Moodle sedang tidak dapat dijangkau oleh backend.')}
            </p>
          </div>
          <div className="flex items-center gap-2 pl-7 sm:pl-0">
            {moodleStatusLoading ? (
              <Spinner size="sm" />
            ) : isMoodleConnected ? (
              <Badge tone="success">Terhubung</Badge>
            ) : (
              <Badge tone="danger">Terputus</Badge>
            )}
          </div>
        </div>

        {/* Item 4 (khusus FULL): Seluruh Konten Jenis Aktif Disetujui */}
        {isFull && (
          <div className="p-3.5 space-y-2.5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold ${
                    isContentsReady ? 'bg-success text-white' : 'bg-muted/20 text-muted'
                  }`}>
                    {isContentsReady ? '✓' : '4'}
                  </span>
                  <span className="font-semibold text-sm">Seluruh Konten Jenis Aktif Disetujui</span>
                </div>
                <p className="mt-1 text-xs text-muted pl-7">
                  {contentsLoading && !readiness.hasAnyContent
                    ? 'Memeriksa status persetujuan konten mingguan…'
                    : !readiness.hasActiveContents
                    ? 'Belum ada konten jenis aktif yang dibuat untuk alur kerja ini.'
                    : readiness.allApproved
                    ? `Seluruh ${readiness.approvedCount} konten jenis aktif telah disetujui dan siap diterbitkan ke Moodle.`
                    : `Masih terdapat ${readiness.unapprovedItems.length} dari ${readiness.activeCount} konten jenis aktif yang belum berstatus Disetujui.`}
                </p>
              </div>
              <div className="flex items-center gap-2 pl-7 sm:pl-0">
                {contentsLoading && !readiness.hasAnyContent ? (
                  <Spinner size="sm" />
                ) : !readiness.hasActiveContents ? (
                  <>
                    <Badge tone="warning">Belum Ada Konten</Badge>
                    <Link
                      to="../content"
                      relative="path"
                      className="btn btn--secondary btn--xs"
                    >
                      Buka Tab Konten →
                    </Link>
                  </>
                ) : readiness.allApproved ? (
                  <Badge tone="success">Semua Disetujui ({readiness.approvedCount} konten)</Badge>
                ) : (
                  <>
                    <Badge tone="warning">{readiness.unapprovedItems.length} Belum Disetujui</Badge>
                    <Link
                      to="../review"
                      relative="path"
                      className="btn btn--secondary btn--xs"
                    >
                      Buka Tab Review →
                    </Link>
                  </>
                )}
              </div>
            </div>

            {readiness.unapprovedItems.length > 0 && (
              <div className="pl-7">
                <Alert tone="warning" title="Daftar konten yang belum disetujui">
                  <ul className="mt-1 space-y-1 text-xs">
                    {unapprovedPreview.map((item, idx) => {
                      const statusMeta = CONTENT_STATUS_META[item.status] ?? {
                        label: item.status ?? 'Belum disetujui',
                        tone: 'neutral',
                      };
                      return (
                        <li
                          key={item.id ?? `${item.week_number}-${item.kind}-${idx}`}
                          className="flex flex-wrap items-center justify-between gap-2 rounded border border-line/70 bg-surface px-2.5 py-1.5"
                        >
                          <span className="min-w-0 flex-1 truncate">
                            <strong>Minggu {item.week_number ?? '-'}</strong> · {CONTENT_KIND_LABELS[item.kind] ?? item.kind} — {item.title || 'Tanpa judul'}
                          </span>
                          <Badge tone={statusMeta.tone}>{statusMeta.label}</Badge>
                        </li>
                      );
                    })}
                  </ul>
                  {remainingUnapproved > 0 && (
                    <p className="mt-1.5 text-xs text-muted">
                      Dan {remainingUnapproved} konten lainnya. Selesaikan persetujuan pada{' '}
                      <Link to="../review" relative="path" className="font-semibold underline">halaman Review</Link>.
                    </p>
                  )}
                </Alert>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Banner Ringkasan Kesiapan & Tombol Aksi */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-t border-line pt-4">
        <div>
          {allReady ? (
            <p className="text-sm font-medium text-success flex items-center gap-1.5">
              <span>✓</span>{' '}
              {isFull
                ? `Semua prasyarat terpenuhi. ${weekCount} section dan ${readiness.approvedCount} activity siap diterapkan ke Moodle.`
                : `Semua prasyarat terpenuhi. Struktur ${weekCount} minggu siap diterapkan ke Moodle.`}
            </p>
          ) : (
            <p className="text-sm text-muted">
              Lengkapi seluruh prasyarat di atas untuk mengaktifkan tombol eksekusi.
            </p>
          )}
        </div>

        <button
          type="button"
          className="btn btn--primary"
          disabled={!allReady || executing}
          onClick={() => setConfirmOpen(true)}
        >
          {executing
            ? 'Memulai eksekusi…'
            : isFull
            ? 'Eksekusi Course ke Moodle'
            : 'Eksekusi Struktur Course'}
        </button>
      </div>

      {/* Dialog Konfirmasi Sebelum Eksekusi */}
      <ExecutionConfirmModal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={handleStart}
        courseTarget={courseTarget || (targetId ? { fullname: targetName, id: targetId } : null)}
        weekCount={weekCount}
        scope={selectedScope}
        activityCount={readiness.approvedCount}
        activityCountsByKind={readiness.countsByKind}
        pending={executing}
      />
    </Card>
  );
}
