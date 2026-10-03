import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { useApi } from '../../hooks/useApi';
import { getActionEvents, getRecentCourses, getCoursesByClassification } from '../../services/moodle/moodleApi';
import { PageContainer } from '../../components/MoodleLayout';
import { Card, EmptyState, ErrorAlert, Spinner } from '../../components/ui';
import ActivityIcon from '../../components/moodle/ActivityIcon';
import CourseCard from '../../components/moodle/CourseCard';
import { cmidFromUrl, formatUnixDay, formatUnixTime } from '../../utils/format';

function Timeline() {
  const { data: events, error, loading } = useApi(() => getActionEvents({ limit: 20 }));

  if (loading && !events) return <Spinner />;
  if (error) return <ErrorAlert error={error} />;
  if (!events.length) {
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
  const recent = useApi(() => getRecentCourses(user.id, 4), [user.id]);
  const all = useApi(() => getCoursesByClassification('inprogress'));
  const teacherIds = new Set(user.teacherCourseIds);

  const courses = recent.data?.length ? recent.data : (all.data ?? []).slice(0, 4);
  const teaching = (all.data ?? []).filter((c) => teacherIds.has(c.id));

  return (
    <PageContainer>
      <h1 className="moodle-h1 mb-6">Halo, {user.firstname}! 👋</h1>

      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
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
            <ErrorAlert error={recent.error || all.error} />
            {(recent.loading || all.loading) && !courses.length ? (
              <Spinner />
            ) : courses.length ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {courses.map((c) => (
                  <CourseCard key={c.id} course={c} isTeacher={teacherIds.has(c.id)} />
                ))}
              </div>
            ) : (
              <EmptyState title="Anda belum terdaftar di kursus mana pun." />
            )}
          </Card>
        </div>

        <aside className="flex flex-col gap-5">
          {user.role === 'dosen' ? (
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
                  <p className="text-sm text-muted">{user.isAdmin ? 'Anda admin situs.' : 'Belum ada.'}</p>
                )}
              </Card>
              <Card title="Generator Konten AI">
                <p className="mb-3 text-sm text-muted">Isi konten course otomatis dari RPS, review, lalu kirim ke Moodle.</p>
                <Link to="/ai" className="btn btn--primary btn--sm">
                  Buka Generator AI
                </Link>
              </Card>
            </>
          ) : (
            <Card title="Ringkasan belajar">
              {all.data ? (
                <ul className="list">
                  {all.data.map((c) => (
                    <li key={c.id} className="list__split">
                      <Link to={`/course/${c.id}`} className="min-w-0 truncate">
                        {c.shortname}
                      </Link>
                      <span className="text-sm text-muted">{c.progress != null ? `${Math.round(c.progress)}%` : '-'}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <Spinner />
              )}
            </Card>
          )}
        </aside>
      </div>
    </PageContainer>
  );
}
