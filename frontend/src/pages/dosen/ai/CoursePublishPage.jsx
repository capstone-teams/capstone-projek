import { useState } from 'react';
import { useCourse } from '../../../hooks/useCourse';
import { useApi } from '../../../hooks/useApi';
import { getWorkflowPlan } from '../../../services/coursePlanService';
import { getMoodleStatus } from '../../../services/moodleIntegrationService';
import { listExecutions } from '../../../services/executionService';
import ExecutionReadinessCard from '../../../components/ai/course/ExecutionReadinessCard';
import { Alert, Badge, Card, Spinner } from '../../../components/ui';

export default function CoursePublishPage() {
  const { course, moodleCourse, workflow, workflowId, refresh } = useCourse();
  const [newExecution, setNewExecution] = useState(null);

  // Ambil course plan versi terbaru dari workflow aktif
  const planQuery = useApi(
    () => (workflowId ? getWorkflowPlan(workflowId).catch(() => null) : null),
    [workflowId]
  );

  // Cek status koneksi Moodle backend
  const moodleStatusQuery = useApi(
    () => getMoodleStatus().catch((err) => ({ connected: false, message: err?.message })),
    []
  );

  // Ambil riwayat eksekusi workflow ini jika ada
  const executionsQuery = useApi(
    () => (workflowId ? listExecutions(workflowId).catch(() => []) : []),
    [workflowId]
  );

  const executions = executionsQuery.data ?? [];
  const latestExecution = newExecution || executions[0] || null;

  const handleExecutionStarted = (execution) => {
    setNewExecution(execution);
    executionsQuery.reload({ silent: true });
    refresh?.();
  };

  const targetCourse = moodleCourse || (workflow?.moodle_course_id ? { id: workflow.moodle_course_id } : null);

  return (
    <div className="stack">
      {/* Kartu Pemeriksaan Kesiapan & Inisiasi Eksekusi Struktur (FE-13.1) */}
      <ExecutionReadinessCard
        workflowId={workflowId}
        workflow={workflow}
        courseTarget={targetCourse}
        plan={planQuery.data}
        planLoading={planQuery.loading}
        moodleStatus={moodleStatusQuery.data}
        moodleStatusLoading={moodleStatusQuery.loading}
        onExecutionStarted={handleExecutionStarted}
      />

      {/* Status Eksekusi Terakhir / Aktif (FE-13.1 transisi ke FE-13.2) */}
      {latestExecution && (
        <Card
          title="Status Eksekusi Struktur Moodle"
          actions={
            <Badge
              tone={
                latestExecution.status === 'SUCCESS'
                  ? 'success'
                  : latestExecution.status === 'FAILED'
                  ? 'danger'
                  : 'info'
              }
            >
              {latestExecution.status}
            </Badge>
          }
        >
          <div className="space-y-3">
            <p className="text-sm">
              Eksekusi ID: <span className="font-mono text-xs font-semibold">{latestExecution.execution_id}</span> · Cakupan: <span className="font-mono text-xs">{latestExecution.scope}</span>
            </p>

            {latestExecution.status === 'PENDING' || latestExecution.status === 'RUNNING' ? (
              <Alert tone="info">
                Eksekusi struktur 16 minggu sedang dijadwalkan dan berjalan di background Moodle. Anda dapat memantau progres operasi tiap minggu di bawah.
              </Alert>
            ) : latestExecution.status === 'SUCCESS' ? (
              <Alert tone="success">
                Struktur 16 section mingguan telah berhasil dibuat pada kursus Moodle target.
              </Alert>
            ) : latestExecution.status === 'FAILED' ? (
              <Alert tone="danger" title="Eksekusi Terhenti">
                {latestExecution.error_message || 'Sebagian atau seluruh operasi struktur gagal diterapkan ke Moodle.'}
              </Alert>
            ) : null}

            {latestExecution.summary && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center pt-2">
                <div className="rounded border border-line p-2">
                  <div className="text-xs text-muted">Total Operasi</div>
                  <div className="text-lg font-bold">{latestExecution.summary.total ?? 0}</div>
                </div>
                <div className="rounded border border-line p-2 text-success">
                  <div className="text-xs text-muted">Berhasil</div>
                  <div className="text-lg font-bold">{latestExecution.summary.success ?? 0}</div>
                </div>
                <div className="rounded border border-line p-2 text-danger">
                  <div className="text-xs text-muted">Gagal</div>
                  <div className="text-lg font-bold">{latestExecution.summary.failed ?? 0}</div>
                </div>
                <div className="rounded border border-line p-2 text-muted">
                  <div className="text-xs text-muted">Dilewati</div>
                  <div className="text-lg font-bold">{latestExecution.summary.skipped ?? 0}</div>
                </div>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
