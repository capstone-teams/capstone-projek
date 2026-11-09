import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { useApi } from '../../hooks/useApi';
import { getActionEvents, getRecentCourses, getCoursesByClassification } from '../../services/moodle/moodleApi';
import { getMoodleCourses } from '../../services/moodleIntegrationService';
import { listRps } from '../../services/rpsService';
import { listWorkflows } from '../../services/workflowService';
import { PageContainer } from '../../components/layout/MoodleLayout';
import { Card, EmptyState, ErrorAlert, Modal, Spinner } from '../../components/ui';
import ActivityIcon from '../../components/moodle/ActivityIcon';
import CourseCard from '../../components/moodle/CourseCard';
import RpsStatusBadge from '../../components/ai/RpsStatusBadge';
import WorkflowStatusBadge from '../../components/ai/WorkflowStatusBadge';
import RpsUploadForm from '../../components/ai/RpsUploadForm';
import { cmidFromUrl, formatDateTime, formatUnixDay, formatUnixTime } from '../../utils/format';
import { ROLE } from '../../types/auth';
import { RPS_STATUS } from '../../utils/rpsStatus';
import { WORKFLOW_STATUS, workflowStatusOf } from '../../utils/workflowStatus';

function Timeline() {
  const { data: events, error, loading } = useApi(() => getActionEvents({ limit: 20 }).catch(() => []));

  if (loading && !events) return <Spinner />;
  if (error) return <ErrorAlert error={error} />;
  if (!events || !events.length) {
    return <EmptyState title="Tidak ada aktivitas yang memerlukan tindakan.">Tenggat tugas dan kuis akan tampil di sini.</EmptyState>;
  }

  const groups = [];
  events.forEach((ev) => {
    const day = formatUnixDay(ev.timesort);
    const last = groups.at(-1);
    if (last?.day === day) last.items.push(ev);
    else groups.push({ day, items: [ev] });
  });

  return (
    <div className="flex flex-col gap-4">
      {groups.map((g) => (
        <div key={g.day}>
          <h3 className="mb-2 border-b border-line pb-1.5 text-sm font-bold">{g.day}</h3>
          <ul className="flex flex-col gap-2">
            {g.items.map((ev) => {
              const cmid = cmidFromUrl(ev.url);
              const to = cmid ? `/course/${ev.course.id}/mod/${cmid}` : `/course/${ev.course.id}`;
              return (
                <li key={ev.id} className="flex flex-wrap items-center gap-3">
                  <span className="w-12 text-sm text-muted tabular-nums">{formatUnixTime(ev.timesort)}</span>
                  <ActivityIcon modname={ev.modulename} src={ev.icon?.iconurl} size="sm" />
                  <Link to={to} className="min-w-0 flex-1 truncate font-medium text-sm">
                    {ev.name}
                  </Link>
                  <span className="text-xs text-muted">{ev.course?.shortname}</span>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}

function getCourseTargetForRps(rpsItem, workflowsList, coursesList, teachingList) {
  if (typeof sessionStorage !== 'undefined') {
    for (const c of coursesList) {
      if (sessionStorage.getItem(`agentic-lms.course-rps.${c.id}`) === rpsItem.id) {
        return c.id;
      }
    }
  }

  const wf = rpsItem.workflow_id
    ? workflowsList.find((w) => w.id === rpsItem.workflow_id)
    : workflowsList.find((w) => w.rps_id === rpsItem.id);

  if (wf) {
    if (wf.moodle_course_id) return wf.moodle_course_id;
    if (typeof sessionStorage !== 'undefined') {
      try {
        const stored = JSON.parse(sessionStorage.getItem('agentic-lms.workflow-targets')) ?? {};
        const matchedKey = Object.keys(stored).find((k) => k === wf.id || k.startsWith(`${wf.id}:`));
        if (matchedKey && stored[matchedKey]) return stored[matchedKey];
        for (const c of coursesList) {
          if (sessionStorage.getItem(`agentic-lms.course-workflow.${c.id}`) === wf.id) {
            return c.id;
          }
        }
      } catch {
        // ignore
      }
    }
  }

  // Fallback: Jika dosen hanya mengampu 1 kursus (kasus utama Dosen Demo),
  // semua berkas RPS milik dosen ini diasosiasikan ke kursus tersebut.
  const teaching = teachingList?.length ? teachingList : coursesList;
  if (teaching && teaching.length === 1) {
    return teaching[0].id;
  }

  return null;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const isDosen = user?.role === ROLE.DOSEN || user?.role === 'dosen' || user?.role === 'INSTRUCTOR';
  const [uploadModalOpen, setUploadModalOpen] = useState(false);

  // Kursus yang baru diakses (GET /courses/recent)
  const recent = useApi(() => getRecentCourses(user?.id, 4).catch(() => []), [user?.id]);

  // Kursus dosen: dari Moodle API terlebih dahulu, fallback ke gateway bila Moodle gagal
  const coursesQuery = useApi(async () => {
    try {
      const moodle = await getCoursesByClassification('all');
      if (Array.isArray(moodle) && moodle.length) return moodle;
      const moodleCourses = await getMoodleCourses();
      if (moodleCourses?.courses?.length) return moodleCourses.courses;
      return [];
    } catch {
      const gateway = await getMoodleCourses().catch(() => null);
      return gateway?.courses ?? [];
    }
  });

  const rpsQuery = useApi(() => (isDosen ? listRps().catch(() => ({ items: [] })) : null), [isDosen]);
  const workflowsQuery = useApi(() => (isDosen ? listWorkflows().catch(() => []) : null), [isDosen]);

  const teacherIds = new Set(user?.teacherCourseIds ?? []);
  const coursesList = coursesQuery.data ?? [];
  const courses = recent.data?.length ? recent.data : coursesList.slice(0, 4);
  const isTeacherCourse = (courseId) => isDosen || teacherIds.has(courseId);
  const teaching = isDosen ? coursesList : coursesList.filter((c) => teacherIds.has(c.id));
  const defaultCourseId = teaching[0]?.id || coursesList[0]?.id || 2;

  const rpsList = rpsQuery.data?.items ?? (Array.isArray(rpsQuery.data) ? rpsQuery.data : []);
  const workflowsList = Array.isArray(workflowsQuery.data)
    ? workflowsQuery.data
    : (workflowsQuery.data?.items ?? []);

  // Opsi 1: Tampilkan dokumen RPS aktif per kursus dosen.
  // Jika suatu kursus memiliki beberapa berkas RPS (misal berkas lama digantikan berkas baru),
  // hanya berkas terbaru yang aktif yang ditampilkan pada kartu dasbor.
  const activeRpsList = useMemo(() => {
    if (!rpsList.length) return [];
    if (rpsList.length === 1) return rpsList;

    const seenCourses = new Set();
    const result = [];
    const unassigned = [];

    // Urutkan dokumen dari yang terbaru berdasarkan created_at
    const sorted = [...rpsList].sort((a, b) => {
      const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
      const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
      return timeB - timeA;
    });

    for (const item of sorted) {
      const courseId = getCourseTargetForRps(item, workflowsList, coursesList, teaching);

      if (courseId) {
        // Jika kursus ini sudah memiliki RPS aktif terbaru di daftar, lewati berkas lama yang tergantikan
        if (seenCourses.has(String(courseId))) {
          continue;
        }
        seenCourses.add(String(courseId));
        result.push({ ...item, targetCourseId: courseId });
      } else {
        // Dokumen yang belum ditautkan ke kursus:
        // Tampilkan dokumen aktif/siap (ANALYZED, PROCESSING, PROCESSED, ANALYZING, UPLOADED)
        const isActiveOrReady = [
          RPS_STATUS.UPLOADED,
          RPS_STATUS.PROCESSING,
          RPS_STATUS.PROCESSED,
          RPS_STATUS.ANALYZING,
          RPS_STATUS.ANALYZED,
        ].includes(item.status);

        if (isActiveOrReady) {
          unassigned.push(item);
        }
      }
    }

    // Masukkan dokumen unassigned aktif terbaru (maksimal 2)
    for (const item of unassigned.slice(0, 2)) {
      result.push(item);
    }

    // Fallback: Jika setelah filter tidak ada dokumen sama sekali namun rpsList ada,
    // tampilkan dokumen terbaru dari riwayat agar kartu dasbor tidak kosong
    if (result.length === 0 && sorted.length > 0) {
      result.push(sorted[0]);
    }

    return result;
  }, [rpsList, workflowsList, coursesList, teaching]);

  return (
    <PageContainer>
      <div className="mb-6">
        <h1 className="moodle-h1">Halo, {user?.firstname}! 👋</h1>
        {isDosen && (
          <p className="mt-1 text-sm text-muted">
            Dasbor ringkasan aktivitas pengajaran dan otomatisasi kurikulum berbasis AI.
          </p>
        )}
      </div>

      <div className="grid items-start gap-5 lg:grid-cols-[1fr_360px]">
        <div className="flex min-w-0 flex-col gap-5">
          <Card title="Timeline">
            <Timeline />
          </Card>

          <Card
            title={recent.data?.length ? 'Kursus yang baru diakses' : 'Kursus berjalan'}
            actions={
              <Link to="/my/courses" className="text-sm">
                Lihat semua
              </Link>
            }
          >
            <ErrorAlert error={recent.error || coursesQuery.error} />
            {(recent.loading || coursesQuery.loading) && !courses.length ? (
              <Spinner />
            ) : courses.length ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {courses.map((c) => (
                  <CourseCard key={c.id} course={c} isTeacher={isTeacherCourse(c.id)} />
                ))}
              </div>
            ) : (
              <EmptyState title="Anda belum terdaftar di kursus mana pun." />
            )}
          </Card>
        </div>

        <div className="grid gap-5">
          {isDosen ? (
            <>
              <Card title="Kursus yang Anda ajar">
                {teaching.length ? (
                  <ul className="list">
                    {teaching.map((c) => (
                      <li key={c.id}>
                        <Link to={`/course/${c.id}`}>{c.fullname}</Link>
                        <div className="text-xs text-muted">{c.shortname}</div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted">{user?.isAdmin ? 'Anda admin situs.' : 'Belum ada.'}</p>
                )}
              </Card>

              {/* Ringkasan RPS & Dokumen Akademik (FE-11.1) */}
              <Card
                title="RPS & Dokumen Akademik"
                actions={
                  <div className="flex items-center gap-3">
                    <Link
                      to={`/course/${defaultCourseId}/ai/workflows`}
                      className="text-xs text-muted hover:text-ink hover:underline"
                      title="Lihat riwayat alur kerja lengkap di monitoring"
                    >
                      Monitoring ↗
                    </Link>
                    <button
                      type="button"
                      className="cursor-pointer text-sm font-semibold text-primary hover:underline"
                      onClick={() => setUploadModalOpen(true)}
                    >
                      + Unggah
                    </button>
                  </div>
                }
              >
                <ErrorAlert error={rpsQuery.error} />
                {rpsQuery.loading && !activeRpsList.length ? (
                  <Spinner label="Memuat dokumen RPS…" />
                ) : activeRpsList.length === 0 ? (
                  <EmptyState
                    title="Belum ada dokumen RPS."
                    action={
                      <button
                        type="button"
                        className="btn btn--primary btn--sm"
                        onClick={() => setUploadModalOpen(true)}
                      >
                        Unggah RPS Sekarang
                      </button>
                    }
                  >
                    Unggah dokumen RPS mata kuliah untuk mulai menyusun rencana dan konten secara otomatis.
                  </EmptyState>
                ) : (
                  <ul className="flex flex-col gap-2.5">
                    {activeRpsList.slice(0, 6).map((item) => {
                      const relatedWf = item.workflow_id
                        ? workflowsList.find((w) => w.id === item.workflow_id)
                        : workflowsList.find((w) => w.rps_id === item.id);
                      const wfStatus = relatedWf ? (workflowStatusOf(relatedWf) || relatedWf.status) : null;
                      const isReview = wfStatus === WORKFLOW_STATUS.WAITING_FOR_REVIEW;
                      const isFailed = item.status === RPS_STATUS.FAILED || wfStatus === WORKFLOW_STATUS.FAILED;
                      const isAnalyzed = item.status === RPS_STATUS.ANALYZED && !isReview && !isFailed;
                      const rpsCourseId = item.targetCourseId || relatedWf?.moodle_course_id;
                      const courseInfo = rpsCourseId ? coursesList.find((c) => String(c.id) === String(rpsCourseId)) : null;
                      const targetCourseId = rpsCourseId || defaultCourseId;

                      const reviewUrl = (relatedWf?.stage === 'content_generation' || relatedWf?.stage === 'content_review' || relatedWf?.stage === 'instructor_review')
                        ? `/course/${targetCourseId}/ai/review`
                        : `/course/${targetCourseId}/ai/plan`;

                      return (
                        <li
                          key={item.id}
                          className="rounded-lg border border-line p-2.5 transition-colors"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <span className="truncate font-semibold text-sm" title={item.filename}>
                              {item.filename}
                            </span>
                            {relatedWf && (isReview || wfStatus === WORKFLOW_STATUS.RUNNING) ? (
                              <WorkflowStatusBadge workflow={relatedWf} />
                            ) : (
                              <RpsStatusBadge status={item.status} />
                            )}
                          </div>
                          <div className="mt-2 flex items-center justify-between text-xs text-muted">
                            <span className="flex items-center gap-1.5 truncate">
                              {courseInfo && (
                                <span className="font-medium text-ink/80 truncate max-w-[120px]" title={courseInfo.fullname}>
                                  {courseInfo.shortname || courseInfo.fullname} ·
                                </span>
                              )}
                              <span>{item.created_at ? formatDateTime(item.created_at) : 'Baru'}</span>
                            </span>
                            <div className="flex items-center gap-2">
                              {isReview ? (
                                <Link
                                  to={reviewUrl}
                                  className="font-medium text-primary hover:underline"
                                >
                                  Review Sekarang →
                                </Link>
                              ) : isFailed ? (
                                <Link
                                  to={
                                    item.workflow_id
                                      ? `/course/${targetCourseId}/ai/workflows?workflow=${item.workflow_id}`
                                      : `/course/${targetCourseId}/ai/rps?rps=${item.id}`
                                  }
                                  className="font-medium text-danger hover:underline"
                                >
                                  Lihat Masalah
                                </Link>
                              ) : isAnalyzed ? (
                                <Link
                                  to={`/course/${targetCourseId}/ai/rps?rps=${item.id}`}
                                  className="font-medium text-primary hover:underline"
                                >
                                  Hasil Analisis
                                </Link>
                              ) : item.workflow_id ? (
                                <Link
                                  to={`/course/${targetCourseId}/ai/workflows?workflow=${item.workflow_id}`}
                                  className="font-medium text-primary hover:underline"
                                >
                                  Pantau Proses
                                </Link>
                              ) : null}
                            </div>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </Card>
            </>
          ) : (
            <Card title="Ringkasan belajar">
              {coursesQuery.loading && !coursesQuery.data ? (
                <Spinner />
              ) : coursesList.length ? (
                <ul className="list">
                  {coursesList.map((c) => (
                    <li key={c.id} className="list__split">
                      <Link to={`/course/${c.id}`} className="min-w-0 truncate">
                        {c.shortname}
                      </Link>
                      <span className="text-xs text-muted">{c.fullname}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState title="Belum ada kursus." />
              )}
            </Card>
          )}
        </div>
      </div>

      {/* Modal Unggah RPS Cepat dari Dasbor */}
      {isDosen && uploadModalOpen && (
        <Modal
          open={uploadModalOpen}
          title="Unggah Dokumen RPS"
          onClose={() => setUploadModalOpen(false)}
        >
          <p className="mb-4 text-xs text-muted">
            Unggah berkas RPS (PDF atau DOCX) untuk dianalisis oleh AI. Hasil analisis akan otomatis tercantum pada daftar dokumen.
          </p>
          <RpsUploadForm
            onUploaded={async ({ rps }) => {
              if (rps?.id) {
                setUploadModalOpen(false);
                rpsQuery.reload({ silent: true });
                workflowsQuery.reload({ silent: true });
              }
            }}
          />
        </Modal>
      )}
    </PageContainer>
  );
}
