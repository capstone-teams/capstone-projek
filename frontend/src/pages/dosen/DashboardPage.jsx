import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { useApi } from '../../hooks/useApi';
import { getActionEvents, getRecentCourses, getCoursesByClassification } from '../../services/moodle/moodleApi';
import { PageContainer } from '../../components/layout/MoodleLayout';
import { Card, EmptyState, ErrorAlert, Spinner } from '../../components/ui';
import ActivityIcon from '../../components/moodle/ActivityIcon';
import CourseCard from '../../components/moodle/CourseCard';
import { cmidFromUrl, formatUnixDay, formatUnixTime } from '../../utils/format';
import { ROLE } from '../../types/auth';

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
  const isDosen = user?.role === ROLE.DOSEN || user?.role === 'dosen';
  const recent = useApi(() => getRecentCourses(user?.id, 4).catch(() => []), [user?.id]);
  // Kursus berjalan: lewat Backend Gateway bila tidak ada sesi Moodle di browser (lihat getCoursesByClassification).
  // Galatnya ditampilkan agar gangguan layanan tidak terbaca sebagai "belum terdaftar di kursus mana pun".
  const coursesQuery = useApi(() => getCoursesByClassification('inprogress'));
  const teacherIds = new Set(user?.teacherCourseIds ?? []);

  const coursesList = coursesQuery.data ?? [];
  const courses = recent.data?.length ? recent.data : coursesList.slice(0, 4);
  const isTeacherCourse = (courseId) => isDosen || teacherIds.has(courseId);
  const teaching = isDosen ? coursesList : coursesList.filter((c) => teacherIds.has(c.id));

  return (
    <PageContainer>
      <h1 className="moodle-h1 mb-6">Halo, {user.firstname}! 👋</h1>

      <div className="grid items-start gap-5 ">
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
            {coursesQuery.error && !courses.length && (
              <button type="button" className="btn btn--ghost btn--sm" onClick={() => coursesQuery.reload()}>Coba lagi</button>
            )}
            {(recent.loading || coursesQuery.loading) && !courses.length ? (
              <Spinner />
            ) : coursesQuery.error && !courses.length ? null : courses.length ? (
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
          {user.role === ROLE.DOSEN ? (
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
                  <p className="text-sm text-muted">
                    {coursesQuery.error ? 'Daftar kursus belum dapat dimuat.' : user.isAdmin ? 'Anda admin situs.' : 'Belum ada.'}
                  </p>
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
    </PageContainer>
  );
}
