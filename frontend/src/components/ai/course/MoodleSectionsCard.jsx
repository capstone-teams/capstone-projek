import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { useApi } from '../../../hooks/useApi';
import { getPlan } from '../../../services/courseService';
import { PLAN_STATUS, getWorkflowPlan } from '../../../services/coursePlanService';
import { saveMoodleSection } from '../../../services/moodleIntegrationService';
import { Alert, Card, Modal, ProgressBar } from '../../ui';

/**
 * Section mingguan di kursus Moodle target (POST /integrations/moodle/courses/{id}/sections): satu section
 * "Minggu N: judul" per minggu rencana. Backend mengganti nama section yang nomornya sudah ada, sehingga aman
 * diulang. Hanya tersedia setelah course target dipilih dan rencana disetujui, karena menulis ke Moodle.
 */
export default function MoodleSectionsCard() {
  const { course, workflow, workflowId } = useCourse();
  const target = workflow?.moodle_course_id ?? null;
  const plan = useApi(async () => {
    const latest = workflowId ? await getWorkflowPlan(workflowId).catch(() => null) : null;
    return latest ?? (course?.id ? await getPlan(course.id).catch(() => null) : null);
  }, [workflowId, course?.id]);
  const [confirming, setConfirming] = useState(false);
  const [run, setRun] = useState(null); // { done, failed: [{ week, message }], finished }

  const weeks = plan.data?.weeks ?? [];
  const approved = plan.data?.status === PLAN_STATUS.APPROVED;
  const running = !!run && !run.finished;
  const canRun = !!target && approved && weeks.length > 0 && !running;

  const start = async () => {
    setConfirming(false);
    const state = { done: 0, failed: [], finished: false };
    setRun({ ...state });
    for (const week of weeks) {
      try {
        await saveMoodleSection(target, { name: `Minggu ${week.week_number}: ${week.title}`, section_number: week.week_number });
        state.done += 1;
      } catch (error) {
        state.failed.push({ week: week.week_number, message: error.message });
      }
      setRun({ ...state, failed: [...state.failed] });
    }
    setRun({ ...state, failed: [...state.failed], finished: true });
  };

  return (
    <Card title="Section mingguan di Moodle">
      {!target ? (
        <p className="text-sm text-muted">
          Pilih course target terlebih dahulu.{' '}
          <Link to="../target" relative="path" className="font-semibold">Buka tab Course Target</Link>
        </p>
      ) : plan.loading && !plan.data ? (
        <p className="text-sm text-muted">Memuat rencana…</p>
      ) : !weeks.length ? (
        <p className="text-sm text-muted">Belum ada rencana mingguan untuk dibuat menjadi section.</p>
      ) : (
        <>
          <p className="mb-3 text-sm">
            Membuat atau memperbarui {weeks.length} section (Minggu 1 sampai {weeks.at(-1).week_number}) di kursus Moodle #{target}
            sesuai rencana. Section yang nomornya sudah ada diganti namanya.
          </p>
          {!approved && <p className="mb-3 text-sm text-muted">Tersedia setelah rencana course disetujui.</p>}
          {run && (
            <div className="mb-3" aria-live="polite">
              <ProgressBar completed={run.done + run.failed.length} total={weeks.length} label="Section diproses" />
              {run.finished && run.failed.length === 0 && <Alert tone="success">{run.done} section tersimpan di Moodle.</Alert>}
              {run.failed.length > 0 && (
                <Alert tone="danger" title={`${run.failed.length} section gagal disimpan`}>
                  <ul className="m-0 list-disc pl-5">
                    {run.failed.map((item) => <li key={item.week}>Minggu {item.week}: {item.message}</li>)}
                  </ul>
                </Alert>
              )}
            </div>
          )}
          <button type="button" className="btn btn--primary" disabled={!canRun} onClick={() => setConfirming(true)}>
            {running ? 'Menyimpan…' : run?.finished ? 'Simpan ulang section' : 'Buat section mingguan'}
          </button>
        </>
      )}

      <Modal
        open={confirming}
        title="Buat section mingguan di Moodle?"
        onClose={() => setConfirming(false)}
        footer={
          <>
            <button type="button" className="btn btn--ghost" onClick={() => setConfirming(false)}>Batal</button>
            <button type="button" className="btn btn--primary" onClick={start}>Ya, buat section</button>
          </>
        }
      >
        <p>{weeks.length} section akan dibuat atau diganti namanya di kursus Moodle #{target}. Mahasiswa yang terdaftar dapat melihatnya.</p>
      </Modal>
    </Card>
  );
}
