import { useContext, useState } from 'react';
import { Link } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { useApi } from '../../../hooks/useApi';
import { useWorkflowEvents } from '../../../hooks/useWorkflowEvents';
import { AppStateContext } from '../../../context/appStateContext';
import {
  EXECUTION_STATUS,
  listExecutions,
} from '../../../services/executionService';
import {
  VERIFICATION_STATUS,
  formatVerificationPreconditionError,
  getWorkflowVerification,
  listWorkflowVerifications,
  startWorkflowVerification,
} from '../../../services/verificationService';
import {
  findLatestFinishedFullExecution,
  hasRunningExecution,
  isVerificationPassed,
} from '../../../utils/verificationResult';
import VerificationSummaryCard from '../../../components/ai/course/VerificationSummaryCard';
import VerificationDiscrepanciesTable from '../../../components/ai/course/VerificationDiscrepanciesTable';
import VerificationHistoryCard from '../../../components/ai/course/VerificationHistoryCard';
import { Alert, Card, EmptyState, ErrorAlert, Spinner } from '../../../components/ui';
import { WORKFLOW_API_STATUS } from '../../../utils/workflowStatus';

/**
 * Halaman hasil verifikasi Moodle (FE-18.2, Issue #257) menggunakan endpoint BE-22.2:
 * - status verifikasi terbaru (sesuai / catatan tambahan / tidak sesuai / gagal membaca Moodle),
 * - daftar perbedaan per minggu beserta jenis perbedaan dan status perbaikannya,
 * - tombol jalankan verifikasi / verifikasi ulang beserta perbaikan otomatis,
 * - riwayat hasil verifikasi, dan penanda workflow COMPLETED apabila verifikasi sesuai.
 */
export default function CourseVerificationPage() {
  const { course, moodleCourse, workflow, workflowId, workflowLoading, refresh } = useCourse() ?? {};
  const notify = useContext(AppStateContext)?.notify;
  const [newVerification, setNewVerification] = useState(null);
  const [selectedVerificationId, setSelectedVerificationId] = useState(null);
  const [verifying, setVerifying] = useState(false);
  const [actionError, setActionError] = useState(null);

  const verificationsQuery = useApi(
    () => (workflowId ? listWorkflowVerifications(workflowId) : []),
    [workflowId],
  );
  const executionsQuery = useApi(
    () => (workflowId ? listExecutions(workflowId).catch(() => []) : []),
    [workflowId],
  );

  const rawHistory = verificationsQuery.data ?? [];
  const verifications = newVerification
    && !rawHistory.some((item) => item.verification_id === newVerification.verification_id)
    ? [newVerification, ...rawHistory]
    : rawHistory;

  const latestVerification = verifications[0] ?? null;
  const activeVerificationId = selectedVerificationId || latestVerification?.verification_id || null;
  const viewingOlder = Boolean(
    selectedVerificationId
    && latestVerification
    && selectedVerificationId !== latestVerification.verification_id,
  );

  const detailQuery = useApi(
    () => (workflowId && selectedVerificationId
      ? getWorkflowVerification(workflowId, selectedVerificationId)
      : null),
    [workflowId, selectedVerificationId],
  );

  const activeVerification = viewingOlder
    ? (detailQuery.data || verifications.find((item) => item.verification_id === selectedVerificationId) || null)
    : latestVerification;

  useWorkflowEvents(
    workflowId ? [workflowId] : [],
    (event) => {
      if (
        event?.event === 'WORKFLOW_STAGE_COMPLETED'
        || event?.event === 'WORKFLOW_COMPLETED'
        || event?.event === 'WORKFLOW_FAILED'
        || event?.event === 'WORKFLOW_MOODLE_OPERATION'
      ) {
        verificationsQuery.reload({ silent: true });
        executionsQuery.reload({ silent: true });
        refresh?.();
      }
    },
  );

  const executions = executionsQuery.data ?? [];
  const latestFullExecution = findLatestFinishedFullExecution(executions);
  const executionInProgress = hasRunningExecution(executions);
  // Apabila daftar eksekusi belum memiliki objek FULL secara lokal atau backend yang menentukan,
  // tombol tetap terbuka bila tidak ada eksekusi berjalan dan ada eksekusi FULL selesai.
  const canVerify = Boolean(workflowId && latestFullExecution && !executionInProgress);

  const moodleTargetId = moodleCourse?.id || workflow?.moodle_course_id || course?.moodle_course_id || null;
  const courseUrl = moodleTargetId ? `/course/${moodleTargetId}` : null;
  const workflowCompleted = workflow?.status === WORKFLOW_API_STATUS.COMPLETED;

  const handleRunVerification = async () => {
    if (!workflowId || verifying) return;
    setVerifying(true);
    setActionError(null);
    try {
      const result = await startWorkflowVerification(workflowId);
      setNewVerification(result);
      setSelectedVerificationId(null);
      verificationsQuery.reload({ silent: true });
      executionsQuery.reload({ silent: true });
      refresh?.();

      if (isVerificationPassed(result)) {
        notify?.('Verifikasi Moodle sesuai. Course siap digunakan.', { type: 'success' });
      } else if (result?.status === VERIFICATION_STATUS.PARTIAL) {
        notify?.('Verifikasi selesai dengan catatan aktivitas tambahan di Moodle.', { type: 'warning' });
      } else {
        notify?.('Verifikasi selesai; masih ditemukan perbedaan.', { type: 'warning' });
      }
    } catch (err) {
      setActionError(formatVerificationPreconditionError(err));
    } finally {
      setVerifying(false);
    }
  };

  if (workflowLoading || (workflowId && verificationsQuery.loading && !verificationsQuery.data && !newVerification)) {
    return <Spinner label="Memuat hasil verifikasi Moodle…" />;
  }

  if (workflowId && verificationsQuery.error && !verificationsQuery.data && !newVerification) {
    return (
      <Card title="Hasil Verifikasi Moodle">
        <ErrorAlert error={verificationsQuery.error} />
        <button
          type="button"
          className="btn btn--secondary mt-2"
          disabled={verificationsQuery.loading}
          onClick={() => verificationsQuery.reload()}
        >
          {verificationsQuery.loading ? 'Memuat…' : 'Coba lagi'}
        </button>
      </Card>
    );
  }

  if (!activeVerification) {
    return (
      <Card
        title="Verifikasi Hasil Eksekusi Moodle"
        actions={(
          <div className="flex flex-wrap items-center gap-2">
            {courseUrl && (
              <Link to={courseUrl} className="btn btn--secondary btn--xs">
                Buka Tab Kursus →
              </Link>
            )}
            <Link to="../publish" relative="path" className="btn btn--ghost btn--xs">
              Buka Eksekusi Moodle →
            </Link>
          </div>
        )}
      >
        <ErrorAlert error={actionError} onClose={() => setActionError(null)} />

        {!workflowId ? (
          <EmptyState
            title="Workflow kursus belum dimulai."
            action={<Link to="../rps" relative="path" className="btn btn--primary">Buka tab RPS</Link>}
          >
            Unggah dan analisis RPS terlebih dahulu sebelum menjalankan eksekusi dan verifikasi ke Moodle.
          </EmptyState>
        ) : executionInProgress ? (
          <Alert tone="info" title="Eksekusi Moodle sedang berjalan">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span>Tunggu hingga proses eksekusi selesai sebelum menjalankan verifikasi course.</span>
              <Link to="../publish" relative="path" className="font-semibold underline">
                Pantau di Eksekusi Moodle →
              </Link>
            </div>
          </Alert>
        ) : !latestFullExecution ? (
          <EmptyState
            title="Belum ada eksekusi FULL yang dapat diverifikasi."
            action={(
              <Link to="../publish" relative="path" className="btn btn--primary">
                Buka Eksekusi Moodle →
              </Link>
            )}
          >
            Verifikasi membandingkan isi course Moodle dengan course plan serta seluruh konten yang disetujui pada eksekusi cakupan FULL.
          </EmptyState>
        ) : (
          <div className="space-y-4">
            {latestFullExecution.status === EXECUTION_STATUS.FAILED ? (
              <Alert
                tone="warning"
                title={(latestFullExecution.summary?.failed ?? 0) === 0
                  ? 'Eksekusi FULL mencatat ketidaksesuaian struktur — siap diperiksa'
                  : 'Eksekusi FULL sebelumnya memiliki operasi gagal'}
              >
                {(latestFullExecution.summary?.failed ?? 0) === 0 ? (
                  <>
                    Eksekusi <span className="font-mono font-semibold">{latestFullExecution.execution_id}</span> mengirim{' '}
                    <strong>{latestFullExecution.summary?.success ?? 0}</strong> operasi tanpa kegagalan operasi (<strong>Gagal: 0</strong>),
                    namun pemeriksaan cepat mendeteksi perbedaan di Moodle. Klik <strong>Jalankan Verifikasi</strong> untuk melihat detail{' '}
                    <strong>Diharapkan vs Aktual di Moodle</strong> per item dan mencoba perbaikan otomatis.
                  </>
                ) : (
                  <>
                    Eksekusi <span className="font-mono font-semibold">{latestFullExecution.execution_id}</span> mencatat{' '}
                    <strong>{latestFullExecution.summary?.failed}</strong> operasi gagal. Klik <strong>Jalankan Verifikasi</strong> untuk memeriksa item yang belum sesuai di Moodle dan menjalankan perbaikan otomatis.
                  </>
                )}
              </Alert>
            ) : (
              <Alert tone="info" title="Siap memverifikasi course Moodle">
                Eksekusi Lengkap/FULL (<span className="font-mono font-semibold">{latestFullExecution.execution_id}</span>) sudah selesai.
                Jalankan verifikasi untuk membaca ulang 16 section mingguan dan seluruh activity konten di Moodle serta memperbaiki perbedaan secara otomatis.
              </Alert>
            )}
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                className="btn btn--primary"
                disabled={!canVerify || verifying}
                onClick={handleRunVerification}
              >
                {verifying ? (
                  <span className="inline-flex items-center gap-2">
                    <Spinner size="sm" />
                    <span>Memverifikasi…</span>
                  </span>
                ) : (
                  'Jalankan Verifikasi'
                )}
              </button>
              <span className="text-sm text-muted">
                Sistem membandingkan 16 section mingguan + seluruh activity yang disetujui (aktivitas manual Anda di Moodle tetap dipertahankan).
              </span>
            </div>
          </div>
        )}
      </Card>
    );
  }

  return (
    <div className="stack">
      <ErrorAlert error={actionError} onClose={() => setActionError(null)} />
      {viewingOlder && detailQuery.error && <ErrorAlert error={detailQuery.error} />}

      {executionInProgress && (
        <Alert tone="warning" title="Eksekusi Moodle sedang berjalan">
          Verifikasi ulang dapat dijalankan setelah eksekusi yang sedang berlangsung selesai.
        </Alert>
      )}

      <VerificationSummaryCard
        verification={activeVerification}
        workflowCompleted={workflowCompleted}
        canVerify={canVerify}
        runningExecution={executionInProgress}
        verifying={verifying}
        viewingOlder={viewingOlder}
        courseUrl={courseUrl}
        publishUrl="../publish"
        onVerify={handleRunVerification}
        onBackToLatest={() => setSelectedVerificationId(null)}
      />

      <VerificationDiscrepanciesTable
        key={activeVerification.verification_id}
        verification={activeVerification}
      />

      <VerificationHistoryCard
        verifications={verifications}
        activeVerificationId={activeVerificationId}
        onSelectVerification={(id) => {
          setActionError(null);
          setSelectedVerificationId(id === latestVerification?.verification_id ? null : id);
        }}
      />
    </div>
  );
}
