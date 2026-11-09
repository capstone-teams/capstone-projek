import { useMemo, useState } from 'react';
import { useCourse } from '../../../hooks/useCourse';
import { getMoodleCourse, getMoodleCourseContents, getMoodleCourses, getMoodleStatus } from '../../../services/moodleIntegrationService';
import { getWorkflow, setWorkflowMoodleTarget } from '../../../services/workflowService';
import { getRps } from '../../../services/rpsService';
import { useAction, useApi } from '../../../hooks/useApi';
import {
  Alert,
  Card,
  EmptyState,
  ErrorAlert,
  Modal,
  Spinner,
} from '../../../components/ui';
import MoodleConnectionBanner from '../../../components/moodle/MoodleConnectionBanner';
import CourseTargetCard from '../../../components/ai/course/CourseTargetCard';

/**
 * Halaman Pemilihan Target Course Moodle.
 * Menghubungkan kursus target Moodle dengan alur kerja aktif di backend.
 */
export default function CourseTargetSelectionPage() {
  // Konteks dari layout Generator AI: backend nyata memberi workflow kursus ini, mode mock memberi project /courses.
  const { course, workflowId: contextWorkflowId, refresh } = useCourse() ?? {};

  const [searchQuery, setSearchQuery] = useState('');
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
  const [pendingTargetCourse, setPendingTargetCourse] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  const {
    data: statusData,
    loading: statusLoading,
    error: statusError,
    reload: reloadStatus,
  } = useApi(getMoodleStatus, []);

  const {
    data: coursesData,
    loading: coursesLoading,
    error: coursesError,
    reload: reloadCourses,
  } = useApi(getMoodleCourses, []);

  const {
    data: rpsData,
    loading: rpsLoading,
  } = useApi(async () => {
    if (!course?.rps_id) return null;
    return getRps(course.rps_id);
  }, [course?.rps_id]);

  // Hanya workflow milik kursus atau RPS-nya; tanpa itu target belum dapat dipilih.
  const activeWorkflowId = contextWorkflowId ?? course?.workflow_id ?? rpsData?.workflow_id ?? null;

  const {
    data: workflowDetail,
    loading: workflowDetailLoading,
    error: workflowDetailError,
    reload: reloadWorkflowDetail,
  } = useApi(async () => {
    if (!activeWorkflowId) return null;
    return getWorkflow(activeWorkflowId);
  }, [activeWorkflowId]);

  const savedMoodleCourseId = useMemo(() => {
    if (workflowDetail?.moodle_course_id != null) {
      return String(workflowDetail.moodle_course_id);
    }
    if (course?.workflow_id === activeWorkflowId && course?.moodle_course_id != null) {
      return String(course.moodle_course_id);
    }
    return '';
  }, [workflowDetail, activeWorkflowId, course]);

  const saveTargetAction = useAction(
    (wfId, moodleId) => setWorkflowMoodleTarget(wfId, moodleId),
    { loadingLabel: 'Menyimpan target kursus Moodle…' }
  );

  const handleRetryAll = () => {
    reloadStatus();
    reloadCourses();
    if (activeWorkflowId) reloadWorkflowDetail();
  };

  const courses = useMemo(() => coursesData?.courses ?? [], [coursesData]);
  // Daftar gagal dimuat (bukan kosong): jangan tampilkan pencarian atau keadaan "tidak ada kursus".
  const coursesFailed = !!coursesError && !coursesData;

  // Target saat ini: dari daftar bila ada, selain itu GET /integrations/moodle/courses/{id}.
  const savedInList = courses.find((c) => String(c.id) === savedMoodleCourseId) ?? null;
  const { data: savedDetail } = useApi(
    () => (savedMoodleCourseId && !savedInList && !coursesLoading ? getMoodleCourse(savedMoodleCourseId).catch(() => null) : null),
    [savedMoodleCourseId, !!savedInList, coursesLoading],
  );
  const savedTarget = savedInList ?? savedDetail;

  // Pratinjau isi kursus Moodle yang akan dijadikan target (GET /integrations/moodle/courses/{id}/contents).
  const preview = useApi(
    () => (pendingTargetCourse ? getMoodleCourseContents(pendingTargetCourse.id) : null),
    [pendingTargetCourse?.id],
  );

  const filteredCourses = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return courses;
    return courses.filter(
      (c) =>
        (c.fullname && c.fullname.toLowerCase().includes(query)) ||
        (c.shortname && c.shortname.toLowerCase().includes(query)) ||
        (c.category && c.category.toLowerCase().includes(query))
    );
  }, [courses, searchQuery]);

  const handleRequestSelectCourse = (targetCourse) => {
    setPendingTargetCourse(targetCourse);
    setIsConfirmModalOpen(true);
  };

  const handleCancelModal = () => {
    setIsConfirmModalOpen(false);
    setPendingTargetCourse(null);
  };

  const handleConfirmTarget = async () => {
    if (!activeWorkflowId || !pendingTargetCourse) return;
    try {
      await saveTargetAction.run(activeWorkflowId, pendingTargetCourse.id);
      setSuccessMessage(
        `Kursus "${pendingTargetCourse.shortname} — ${pendingTargetCourse.fullname}" (ID: ${pendingTargetCourse.id}) berhasil disimpan sebagai target Moodle.`
      );
      setIsConfirmModalOpen(false);
      setPendingTargetCourse(null);
      await reloadWorkflowDetail({ silent: true });
      refresh?.();
    } catch {
      // Error tercatat otomatis oleh saveTargetAction.error
    }
  };

  const isWorkflowChecking = workflowDetailLoading || rpsLoading;

  return (
    <div className="stack">
      <Card title="Pilih Target Course Moodle">
        <p className="mb-4 text-sm text-muted">
          Pilih kursus di Moodle LMS ITK yang menjadi tujuan publikasi konten dan aktivitas pembelajaran.
          Hasil rancangan generator AI akan disinkronisasikan ke kursus target yang Anda pilih.
        </p>

        <MoodleConnectionBanner
          status={statusData?.status}
          connected={statusData?.connected}
          siteName={statusData?.site_name}
          message={statusData?.message}
          loading={statusLoading}
          error={statusError}
          onRetry={handleRetryAll}
        />

        {!isWorkflowChecking && !activeWorkflowId && (
          <div className="my-3 rounded-lg border border-warning/40 bg-warning-light p-3 text-sm text-warning">
            <strong>Dokumen RPS belum selesai dianalisis.</strong> Silakan selesaikan analisis RPS terlebih dahulu di tab <strong>RPS</strong> agar target kursus dapat dikaitkan.
          </div>
        )}

        {successMessage && (
          <Alert tone="success" onClose={() => setSuccessMessage(null)}>
            {successMessage}
          </Alert>
        )}

        {savedMoodleCourseId && (
          <p className="mb-3 text-sm" aria-label="Target saat ini">
            <span className="text-muted">Target saat ini: </span>
            <strong>{savedTarget ? `${savedTarget.fullname} (${savedTarget.shortname})` : `Kursus Moodle #${savedMoodleCourseId}`}</strong>
          </p>
        )}

        <ErrorAlert error={workflowDetailError} onClose={reloadWorkflowDetail} />
        <ErrorAlert error={saveTargetAction.error} onClose={saveTargetAction.clearError} />
        {/* Bila status Moodle juga gagal, banner di atas sudah menjelaskannya; pesan yang sama tidak diulang. */}
        {coursesFailed && !statusError && <ErrorAlert error={coursesError} onClose={reloadCourses} />}

        {!coursesFailed && (
        <div className="mb-4 mt-2 flex flex-wrap items-center justify-between gap-3">
          <div className="relative w-full max-w-md">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cari berdasarkan nama, kode (mis. IF2105), atau jurusan…"
              className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink placeholder:text-muted focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              aria-label="Cari kursus target Moodle"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-muted hover:text-ink"
                aria-label="Bersihkan pencarian"
              >
                ✕
              </button>
            )}
          </div>
          <span className="text-xs text-muted">
            Menampilkan {filteredCourses.length} dari {courses.length} kursus
          </span>
        </div>
        )}

        {coursesLoading ? (
          <Spinner label="Memuat daftar kursus dari Moodle…" />
        ) : coursesFailed ? null : courses.length === 0 ? (
          <EmptyState
            title="Tidak ada kursus Moodle ditemukan."
            action={
              <button type="button" className="btn btn--outline" onClick={handleRetryAll}>
                Muat Ulang
              </button>
            }
          >
            Belum ada kursus di Moodle yang dapat dipilih sebagai target.
          </EmptyState>
        ) : filteredCourses.length === 0 ? (
          <EmptyState
            title="Kursus tidak ditemukan."
            action={
              <button
                type="button"
                className="btn btn--outline"
                onClick={() => setSearchQuery('')}
              >
                Reset Pencarian
              </button>
            }
          >
            Tidak ada kursus yang cocok dengan kata kunci &quot;{searchQuery}&quot;. Coba gunakan kata kunci lain.
          </EmptyState>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {filteredCourses.map((c) => (
              <CourseTargetCard
                key={c.id}
                course={c}
                isSelected={Boolean(savedMoodleCourseId && String(c.id) === String(savedMoodleCourseId))}
                onSelect={handleRequestSelectCourse}
                disabled={!activeWorkflowId || saveTargetAction.pending}
              />
            ))}
          </div>
        )}
      </Card>

      <Modal
        open={isConfirmModalOpen}
        title="Konfirmasi Target Course Moodle"
        onClose={handleCancelModal}
        footer={
          <>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={handleCancelModal}
              disabled={saveTargetAction.pending}
            >
              Batal
            </button>
            <button
              type="button"
              className="btn btn--primary"
              disabled={saveTargetAction.pending}
              onClick={handleConfirmTarget}
            >
              {saveTargetAction.pending ? 'Menyimpan…' : 'Konfirmasi & Simpan'}
            </button>
          </>
        }
      >
        {pendingTargetCourse && (
          <div className="space-y-4 text-sm text-ink">
            <p>
              Apakah Anda yakin ingin menetapkan kursus Moodle berikut sebagai target publikasi untuk mata kuliah{' '}
              <strong>{course?.name || 'ini'}</strong>?
            </p>

            <div className="rounded-lg border border-line bg-surface-subtle p-3.5 space-y-2">
              <div className="text-base font-bold text-primary">
                {pendingTargetCourse.fullname}
              </div>
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
                <span>Kode: <strong>{pendingTargetCourse.shortname}</strong></span>
                <span>•</span>
                <span>Moodle ID: <strong>{pendingTargetCourse.id}</strong></span>
                {pendingTargetCourse.category && (
                  <>
                    <span>•</span>
                    <span>Kategori: <strong>{pendingTargetCourse.category}</strong></span>
                  </>
                )}
              </div>
            </div>

            <div className="text-xs" aria-label="Isi kursus Moodle saat ini">
              <p className="mb-1 font-semibold text-ink">Isi kursus di Moodle saat ini</p>
              {preview.loading ? (
                <p className="text-muted">Memuat isi kursus…</p>
              ) : preview.error ? (
                <p className="text-muted">Isi kursus belum dapat dimuat.</p>
              ) : preview.data?.sections?.length ? (
                <ul className="m-0 list-disc space-y-0.5 pl-5 text-muted">
                  {preview.data.sections.slice(0, 6).map((section) => (
                    <li key={section.moodle_section_id ?? section.section_number}>
                      {section.name || `Section ${section.section_number}`} · {section.modules?.length ?? 0} aktivitas
                    </li>
                  ))}
                  {preview.data.sections.length > 6 && <li>dan {preview.data.sections.length - 6} section lainnya</li>}
                </ul>
              ) : (
                <p className="text-muted">Kursus ini masih kosong.</p>
              )}
            </div>

            <p className="text-xs leading-relaxed text-muted">
              Materi pembelajaran, tugas, kuis, dan struktur modul mingguan yang dihasilkan generator AI
              akan dikirimkan dan disinkronisasikan ke kursus Moodle di atas setelah disetujui.
            </p>
          </div>
        )}
      </Modal>
    </div>
  );
}
