import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { useApi } from '../../hooks/useApi';
import { getActionEvents, getRecentCourses, getCoursesByClassification } from '../../services/moodle/moodleApi';
import { getMoodleCourses } from '../../services/moodleIntegrationService';
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

export default function DashboardPage() {
  const { user } = useAuth();
  const isDosen = user?.role === ROLE.DOSEN || user?.role === 'dosen' || user?.role === 'INSTRUCTOR';

  const recent = useApi(() => getRecentCourses(user?.id, 4).catch(() => []), [user?.id]);
  const coursesQuery = useApi(async () => {
    // 1. Coba ambil kursus via Backend API Gateway (Single Gateway)
    const gateway = await getMoodleCourses().catch(() => null);
    if (gateway?.courses?.length) return gateway.courses;

    // 2. Fallback direct WS hanya jika tersedia (mis. mode mock di pengujian)
    try {
      const moodle = await getCoursesByClassification('all');
      if (Array.isArray(moodle) && moodle.length) return moodle;
      return gateway?.courses ?? [];
    } catch {
      return gateway?.courses ?? [];
    }
  });
  const teacherIds = new Set(user?.teacherCourseIds ?? []);

  const coursesList = coursesQuery.data ?? [];
  const courses = recent.data?.length ? recent.data : coursesList.slice(0, 4);
  const isTeacherCourse = (courseId) => isDosen || teacherIds.has(courseId);
  const teaching = isDosen ? coursesList : coursesList.filter((c) => teacherIds.has(c.id));

  return (
    <PageContainer>
      <h1 className="moodle-h1 mb-6">Halo, {user?.firstname || user?.username}! 👋</h1>

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
    </PageContainer>
  );
}
