import { useState } from 'react';
import { useCourse } from '../../../hooks/useCourse';
import { useApi } from '../../../hooks/useApi';
import { usePolling } from '../../../hooks/usePolling';
import { useWorkflowEvents } from '../../../hooks/useWorkflowEvents';
import { getWorkflowPlan } from '../../../services/coursePlanService';
import { listWorkflowContents } from '../../../services/contentService';
import { getInstructorSetup } from '../../../services/instructorService';
import { getMoodleStatus } from '../../../services/moodleIntegrationService';
import {
  getExecution,
  listExecutions,
  retryExecution,
} from '../../../services/executionService';
import { isFullScopeExecution } from '../../../utils/executionReadiness';
import ExecutionReadinessCard from '../../../components/ai/course/ExecutionReadinessCard';
import ExecutionProgressCard from '../../../components/ai/course/ExecutionProgressCard';
import ExecutionHistoryCard from '../../../components/ai/course/ExecutionHistoryCard';
import { Alert } from '../../../components/ui';

export default function CoursePublishPage() {
  const { course, moodleCourse, workflow, workflowId, refresh } = useCourse();
  const [newExecution, setNewExecution] = useState(null);
  const [selectedExecutionId, setSelectedExecutionId] = useState(null);
  const [retrying, setRetrying] = useState(false);

  // Ambil course plan versi terbaru dari workflow aktif
  const planQuery = useApi(
    () => (workflowId ? getWorkflowPlan(workflowId).catch(() => null) : null),
    [workflowId]
  );

  // Ambil daftar konten mingguan & konfigurasi aktivitas untuk prasyarat cakupan FULL (FE-18.1)
  const contentsQuery = useApi(
    () => (workflowId ? listWorkflowContents(workflowId).catch(() => []) : []),
    [workflowId]
  );

  const setupQuery = useApi(
    () => getInstructorSetup().catch(() => null),
    []
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
  const activeExecutionId = selectedExecutionId
    || newExecution?.execution_id
    || executions[0]?.execution_id
    || null;

  // Ambil detail lengkap eksekusi terpilih (termasuk operasi & readback)
  const executionDetailQuery = useApi(
    () => (workflowId && activeExecutionId ? getExecution(workflowId, activeExecutionId).catch(() => null) : null),
    [workflowId, activeExecutionId]
  );

  // Satukan data eksekusi (prioritaskan detail lengkap)
  const currentExecution = executionDetailQuery.data
    || (newExecution?.execution_id === activeExecutionId ? newExecution : null)
    || executions.find((e) => e.execution_id === activeExecutionId)
    || null;

  const isRunning = currentExecution && (currentExecution.status === 'PENDING' || currentExecution.status === 'RUNNING');

  // Pemantauan real-time via WebSocket
  useWorkflowEvents(
    workflowId ? [workflowId] : [],
    (event) => {
      if (event?.event === 'WORKFLOW_MOODLE_OPERATION') {
        executionDetailQuery.reload({ silent: true });
        executionsQuery.reload({ silent: true });
      } else if (event?.event === 'WORKFLOW_STAGE_COMPLETED' || event?.event === 'WORKFLOW_FAILED') {
        executionDetailQuery.reload({ silent: true });
        executionsQuery.reload({ silent: true });
        contentsQuery.reload({ silent: true });
        refresh?.();
      }
    }
  );

  // Polling fallback setiap 3 detik selama eksekusi berstatus PENDING / RUNNING
  usePolling(
    () => {
      executionDetailQuery.reload({ silent: true });
      executionsQuery.reload({ silent: true });
    },
    3000,
    Boolean(isRunning)
  );

  const handleExecutionStarted = (execution) => {
    setNewExecution(execution);
    setSelectedExecutionId(execution.execution_id);
    executionsQuery.reload({ silent: true });
    executionDetailQuery.reload({ silent: true });
    refresh?.();
  };

  const handleRetry = async () => {
    if (!workflowId || !activeExecutionId || retrying) return;
    setRetrying(true);
    try {
      const response = await retryExecution(workflowId, activeExecutionId);
      setNewExecution(response);
      executionDetailQuery.reload({ silent: true });
      executionsQuery.reload({ silent: true });
      refresh?.();
    } catch (err) {
      console.error('Gagal mengulang eksekusi:', err);
    } finally {
      setRetrying(false);
    }
  };

  const moodleTargetId = moodleCourse?.id || workflow?.moodle_course_id || course?.moodle_course_id || null;
  const targetCourse = moodleCourse || (moodleTargetId ? { id: moodleTargetId } : null);
  const courseUrl = moodleTargetId ? `/course/${moodleTargetId}` : null;
  const verificationUrl = currentExecution && !isRunning && isFullScopeExecution(currentExecution)
    ? '../verification'
    : null;

  return (
    <div className="stack">
      {/* Kartu Pemeriksaan Kesiapan & Inisiasi Eksekusi (FE-13.1 & FE-18.1) */}
      <ExecutionReadinessCard
        workflowId={workflowId}
        workflow={workflow}
        courseTarget={targetCourse}
        plan={planQuery.data}
        planLoading={planQuery.loading}
        moodleStatus={moodleStatusQuery.data}
        moodleStatusLoading={moodleStatusQuery.loading}
        contents={contentsQuery.data ?? []}
        contentsLoading={contentsQuery.loading}
        instructorSetup={setupQuery.data}
        onExecutionStarted={handleExecutionStarted}
      />

      {currentExecution?.scope === 'STRUCTURE' && currentExecution?.status === 'SUCCESS' && (
        <Alert tone="info" title="Cakupan eksekusi struktur section (STRUCTURE) selesai">
          Struktur 16 section mingguan sudah dibuat di Moodle. Untuk menerbitkan materi, sumber belajar, tugas, dan kuis menjadi activity di tab Kursus serta melanjutkan ke Step 6 (Verifikasi), pastikan konten sudah disetujui lalu jalankan mode <strong>Lengkap: Struktur + Konten</strong> pada panel di atas.
        </Alert>
      )}

      {/* Kartu Pemantauan Progres, Detail Operasi, dan Verifikasi Read-Back */}
      {currentExecution && (
        <ExecutionProgressCard
          execution={currentExecution}
          plan={planQuery.data}
          courseUrl={courseUrl}
          verificationUrl={verificationUrl}
          onRetry={handleRetry}
          retrying={retrying}
        />
      )}

      {/* Riwayat Eksekusi Sebelumnya */}
      {executions.length > 0 && (
        <ExecutionHistoryCard
          executions={executions}
          activeExecutionId={activeExecutionId}
          onSelectExecution={(id) => {
            setNewExecution(null);
            setSelectedExecutionId(id);
          }}
        />
      )}
    </div>
  );
}
