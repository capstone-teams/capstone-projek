import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useParams } from 'react-router-dom';
import { useAuth } from '../../../hooks/useAuth';
import { useApi } from '../../../hooks/useApi';
import { getCourse, getCourseContents, logCourseView } from '../../../services/moodle/moodleApi';
import { moodleUrl } from '../../../services/moodle/moodleClient';
import { ErrorAlert, Spinner } from '../../../components/ui';

function CourseIndex({ courseId, sections, activeCmid }) {
  const [collapsed, setCollapsed] = useState({});
  return (
    <nav aria-label="Indeks kursus" className="text-sm">
      <ul className="flex flex-col gap-1">
        {sections.map((s) => {
          const isCollapsed = collapsed[s.id];
          return (
            <li key={s.id}>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  className="grid size-6 cursor-pointer place-items-center rounded text-muted hover:bg-black/5"
                  aria-label={isCollapsed ? 'Buka section' : 'Tutup section'}
                  aria-expanded={!isCollapsed}
                  onClick={() => setCollapsed((c) => ({ ...c, [s.id]: !c[s.id] }))}
                >
                  <span className={`transition-transform ${isCollapsed ? '-rotate-90' : ''}`}>▾</span>
                </button>
                <Link to={`/course/${courseId}#section-${s.section}`} className="flex-1 truncate py-1 font-semibold text-ink no-underline hover:underline">
                  {s.name}
                </Link>
              </div>
              {!isCollapsed && (
                <ul className="ml-7 flex flex-col">
                  {s.modules
                    .filter((m) => m.modname !== 'label' && m.uservisible !== false)
                    .map((m) => (
                      <li key={m.id}>
                        <Link
                          to={`/course/${courseId}/mod/${m.id}`}
                          className={`block truncate rounded-lg border border-transparent p-2 no-underline ${
                            m.id === activeCmid ? 'bg-primary text-white hover:text-white' : 'text-ink hover:text-black'
                          }`}
                        >
                          {m.name}
                        </Link>
                      </li>
                    ))}
                </ul>
              )}
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export default function CourseLayout() {
  const params = useParams();
  const courseId = Number(params.courseId);
  const activeCmid = params.cmid ? Number(params.cmid) : null;
  const { user } = useAuth();
  const location = useLocation();
  const [indexOpen, setIndexOpen] = useState(true);
  const [mobileIndex, setMobileIndex] = useState(false);

  const { data, error, loading } = useApi(
    () => Promise.all([getCourse(courseId), getCourseContents(courseId)]).then(([course, sections]) => ({ course, sections })),
    [courseId],
  );

  useEffect(() => {
    logCourseView(courseId);
  }, [courseId]);

  const [lastPath, setLastPath] = useState(location.pathname);
  if (lastPath !== location.pathname) {
    setLastPath(location.pathname);
    setMobileIndex(false);
  }

  if (loading && !data) {
    return (
      <div className="px-8 py-6">
        <Spinner />
      </div>
    );
  }
  if (error || !data?.course) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <ErrorAlert error={error ?? { message: 'Kursus tidak ditemukan atau Anda tidak terdaftar.' }} />
        <Link to="/my/courses">← Kembali ke Kursus saya</Link>
      </div>
    );
  }

  const { course, sections } = data;
  const isTeacher = user.isAdmin || user.teacherCourseIds.includes(courseId);
  const tabs = [
    { to: `/course/${courseId}`, label: 'Kursus', end: true },
    { to: `/course/${courseId}/participants`, label: 'Peserta' },
    { to: `/course/${courseId}/grades`, label: 'Nilai' },
  ];

  const indexPanel = <CourseIndex courseId={courseId} sections={sections} activeCmid={activeCmid} />;

  return (
    <div className="flex min-h-[calc(100vh-61px)]">
      {indexOpen && (
        <aside className="sticky top-[61px] hidden h-[calc(100vh-61px)] w-[285px] shrink-0 overflow-y-auto border-r border-line bg-line-subtle p-3 lg:block">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-bold">Indeks kursus</span>
            <button type="button" className="btn btn--ghost btn--sm" onClick={() => setIndexOpen(false)} aria-label="Tutup indeks kursus">
              ✕
            </button>
          </div>
          {indexPanel}
        </aside>
      )}

      {mobileIndex && (
        <div className="fixed inset-0 top-[61px] z-20 bg-black/30 lg:hidden" onClick={() => setMobileIndex(false)}>
          <aside className="h-full w-[285px] overflow-y-auto bg-line-subtle p-3 shadow-lg" onClick={(e) => e.stopPropagation()}>
            <div className="mb-2 text-sm font-bold">Indeks kursus</div>
            {indexPanel}
          </aside>
        </div>
      )}

      <div className="min-w-0 flex-1">
        <div className="mx-auto w-full max-w-[1100px] px-4 py-5 md:px-8">
          <div className="mb-3 flex items-center gap-2">
            <button
              type="button"
              className={`btn btn--sm ${indexOpen ? 'lg:hidden' : ''}`}
              onClick={() => (window.matchMedia('(min-width: 1024px)').matches ? setIndexOpen(true) : setMobileIndex(true))}
            >
              ☰ Indeks kursus
            </button>
          </div>

          <nav className="mb-1 text-sm text-muted" aria-label="Breadcrumb">
            <Link to="/my/courses">Kursus saya</Link> / <span>{course.shortname}</span>
          </nav>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h1 className="moodle-h1">{course.fullname}</h1>
            <a className="btn btn--sm" href={moodleUrl(`/course/view.php?id=${courseId}`)} target="_blank" rel="noreferrer">
              Buka di Moodle ↗
            </a>
          </div>

          <nav className="tabs" aria-label="Navigasi kursus">
            {tabs.map((t) => (
              <NavLink key={t.to} to={t.to} end={t.end} className="tabs__link">
                {t.label}
              </NavLink>
            ))}
          </nav>

          <Outlet context={{ course, sections, isTeacher }} />
        </div>
      </div>
    </div>
  );
}
