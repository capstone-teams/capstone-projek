import { useState } from 'react';
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
                  <div className="min-w-0 flex-1">
                    <Link to={to} className="block truncate">
                      {ev.activityname || ev.name}
                    </Link>
                    <span className="block truncate text-sm text-muted">
                      {ev.name} · {ev.course.fullnamedisplay ?? ev.course.fullname}
                    </span>
                  </div>
                  {ev.overdue && <span className="text-xs font-bold text-danger">Terlambat</span>}
                  {ev.action?.actionable && (
                    <Link to={to} className="btn btn--secondary btn--sm">
                      {ev.action.name}
                    </Link>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const isDosen = user?.role === ROLE.DOSEN || user?.role === 'dosen' || user?.role === 'INSTRUCTOR';
  const [uploadModalOpen, setUploadModalOpen] = useState(false);

  const recent = useApi(() => getRecentCourses(user?.id, 4).catch(() => []), [user?.id]);
  const coursesQuery = useApi(async () => {
    // 1. Coba ambil kursus via Backend API Gateway (Single Gateway)
    const gateway = await getMoodleCourses().catch(() => null);
    if (gateway?.courses?.length) return gateway.courses;

    // 2. Fallback direct WS hanya jika tersedia (mis. mode mock di pengujian)
    try {
      return await getCoursesByClassification('inprogress');
    } catch {
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

  // Cek apakah ada workflow yang membutuhkan tindakan review dari dosen
  const hasPendingReview = isDosen && workflowsList.some((w) => {
    const status = workflowStatusOf(w) || w.status;
    return status === WORKFLOW_STATUS.WAITING_FOR_REVIEW;
  });

  return (
    <PageContainer>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="moodle-h1">Halo, {user?.firstname}! 👋</h1>
          {isDosen && (
            <p className="mt-1 text-sm text-muted">
              Dasbor ringkasan aktivitas pengajaran dan otomatisasi kurikulum berbasis AI.
            </p>
          )}
        </div>
        {isDosen && (
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="btn btn--primary btn--sm inline-flex items-center gap-1.5"
              onClick={() => setUploadModalOpen(true)}
            >
              <span>+</span> Unggah RPS
            </button>
            <Link to={`/course/${defaultCourseId}/ai/target`} className="btn btn--secondary btn--sm">
              Target Kursus
            </Link>
            <Link to="/user/profile" className="btn btn--ghost btn--sm">
              Preferensi AI
            </Link>
          </div>
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
                {rpsQuery.loading && !rpsList.length ? (
                  <Spinner label="Memuat dokumen RPS…" />
                ) : rpsList.length === 0 ? (
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
                  <>
                    {hasPendingReview && (
                      <div className="mb-3 flex items-center justify-between gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                        <div className="flex items-center gap-1.5 font-medium">
                          <span aria-hidden="true">⚠️</span>
                          <span>Ada dokumen yang menunggu review Anda.</span>
                        </div>
                      </div>
                    )}
                    <ul className="flex flex-col gap-2.5">
                      {rpsList.slice(0, 6).map((item) => {
                        const relatedWf = item.workflow_id
                          ? workflowsList.find((w) => w.id === item.workflow_id)
                          : null;
                        const wfStatus = relatedWf ? (workflowStatusOf(relatedWf) || relatedWf.status) : null;
                        const isReview = wfStatus === WORKFLOW_STATUS.WAITING_FOR_REVIEW;
                        const isFailed = item.status === RPS_STATUS.FAILED || wfStatus === WORKFLOW_STATUS.FAILED;
                        const isAnalyzed = item.status === RPS_STATUS.ANALYZED && !isReview && !isFailed;
                        const rpsCourseId = relatedWf?.moodle_course_id || defaultCourseId;

                        const reviewUrl = (relatedWf?.stage === 'content_generation' || relatedWf?.stage === 'content_review' || relatedWf?.stage === 'instructor_review')
                          ? `/course/${rpsCourseId}/ai/review`
                          : `/course/${rpsCourseId}/ai/plan`;

                        return (
                          <li
                            key={item.id}
                            className={`rounded-lg border p-2.5 transition-colors ${
                              isReview ? 'border-amber-400 bg-amber-50/30' : 'border-line'
                            }`}
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
                              <span>{item.created_at ? formatDateTime(item.created_at) : 'Baru'}</span>
                              <div className="flex items-center gap-2">
                                {isReview ? (
                                  <Link
                                    to={reviewUrl}
                                    className="btn btn--primary btn--xs"
                                  >
                                    Review Sekarang →
                                  </Link>
                                ) : isFailed ? (
                                  <Link
                                    to={
                                      item.workflow_id
                                        ? `/course/${rpsCourseId}/ai/workflows?workflow=${item.workflow_id}`
                                        : `/course/${rpsCourseId}/ai/rps?rps=${item.id}`
                                    }
                                    className="font-medium text-danger hover:underline"
                                  >
                                    Lihat Masalah
                                  </Link>
                                ) : isAnalyzed ? (
                                  <Link
                                    to={`/course/${rpsCourseId}/ai/rps?rps=${item.id}`}
                                    className="font-medium text-primary hover:underline"
                                  >
                                    Hasil Analisis
                                  </Link>
                                ) : item.workflow_id ? (
                                  <Link
                                    to={`/course/${rpsCourseId}/ai/workflows?workflow=${item.workflow_id}`}
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
                  </>
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
                      <span className="text-sm text-muted">{c.progress != null ? `${Math.round(c.progress)}%` : '-'}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted">Belum ada.</p>
              )}
            </Card>
          )}
        </div>
      </div>

      {isDosen && uploadModalOpen && (
        <Modal
          open={uploadModalOpen}
          title="Unggah Dokumen RPS"
          onClose={() => setUploadModalOpen(false)}
        >
          <RpsUploadForm
            onUploaded={({ rps, error }) => {
              if (!error && rps) {
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
