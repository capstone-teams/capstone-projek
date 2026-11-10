import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert, Badge, Card, ErrorAlert, Spinner } from '../../ui';
import ExecutionConfirmModal from './ExecutionConfirmModal';
import {
  EXECUTION_SCOPE,
  formatExecutionPreconditionError,
  startExecution,
} from '../../../services/executionService';
import { PLAN_STATUS } from '../../../services/coursePlanService';

/**
 * Kartu pemeriksaan kesiapan eksekusi struktur Moodle (FE-13.1).
 * Memeriksa 3 prasyarat (Course Plan disetujui, Target kursus terhubung, Koneksi Moodle aktif),
 * menyediakan tautan perbaikan cepat, serta dialog konfirmasi sebelum eksekusi dimulai.
 */
export default function ExecutionReadinessCard({
  workflowId,
  workflow,
  courseTarget,
  plan,
  planLoading = false,
  moodleStatus,
  moodleStatusLoading = false,
  onExecutionStarted,
}) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState(null);

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

  // Kesiapan agregat
  const allReady = Boolean(isPlanApproved && isTargetSet && isMoodleConnected && workflowId);
  const weekCount = plan?.weeks?.length || 16;

  const handleStart = async () => {
    if (!allReady || executing) return;
    setExecuting(true);
    setError(null);
    try {
      const response = await startExecution(workflowId, EXECUTION_SCOPE.STRUCTURE);
      setConfirmOpen(false);
      onExecutionStarted?.(response);
    } catch (err) {
      setConfirmOpen(false);
      setError(formatExecutionPreconditionError(err));
    } finally {
      setExecuting(false);
    }
  };

  return (
    <Card title="Kesiapan Eksekusi Struktur Course">
      <p className="text-sm text-muted mb-4">
        Sebelum struktur mingguan dapat diterapkan ke Moodle, sistem memverifikasi bahwa rencana pembelajaran telah disetujui, target kursus telah dipilih, dan integrasi Moodle dalam keadaan terhubung.
      </p>

      {error && (
        <div className="mb-4">
          <ErrorAlert error={error} onClose={() => setError(null)} />
        </div>
      )}

      {/* Daftar Checklist 3 Prasyarat */}
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
                : 'Rencana pembelajaran harus disetujui terlebih dahulu sebelum struktur dibuat di Moodle.'}
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
      </div>

      {/* Banner Ringkasan Kesiapan & Tombol Aksi */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-t border-line pt-4">
        <div>
          {allReady ? (
            <p className="text-sm font-medium text-success flex items-center gap-1.5">
              <span>✓</span> Semua prasyarat terpenuhi. Struktur {weekCount} minggu siap diterapkan ke Moodle.
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
          {executing ? 'Memulai eksekusi…' : 'Eksekusi Struktur Course'}
        </button>
      </div>

      {/* Dialog Konfirmasi Sebelum Eksekusi */}
      <ExecutionConfirmModal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={handleStart}
        courseTarget={courseTarget || (targetId ? { fullname: targetName, id: targetId } : null)}
        weekCount={weekCount}
        pending={executing}
      />
    </Card>
  );
}
