import { Fragment, useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useParams } from 'react-router-dom';
import { useAuth } from '../../../hooks/useAuth';
import { useApi } from '../../../hooks/useApi';
import { getAdministrationOptions, getCourse, getCourseContents, logCourseView } from '../../../services/moodle/moodleApi';
import { PageContainer } from '../../../components/layout/MoodleLayout';
import { ErrorAlert, ErrorBoundary, Spinner } from '../../../components/ui';
import { ROLE } from '../../../types/auth';

// Rujukan Moodle: hak mengubah kursus (moodle/course:update) dari core_course_get_user_administration_options.
const canUpdate = (options) => options?.[0]?.options.some((o) => o.name === 'update' && o.available) ?? false;

export default function MoodleCourseLayout() {
  const params = useParams();
  const rawCourseId = params.courseId;
  const courseId = Number.isNaN(Number(rawCourseId)) ? rawCourseId : Number(rawCourseId);
  const { user } = useAuth();
  const { pathname } = useLocation();
  // Lanjutan breadcrumb dari halaman di dalam kursus (aktivitas, New <aktivitas>, edit submission).
  const [trail, setTrail] = useState([]);
  const isDosen = user?.role === ROLE.DOSEN || user?.role === 'dosen';

  const { data, error, loading, reload } = useApi(
    () => Promise.all([
      getCourse(courseId),
      getCourseContents(courseId).catch(() => []),
      getAdministrationOptions([courseId]).catch(() => []),
    ])
      .then(([course, sections, options]) => ({
        course,
        sections: sections ?? [],
        canEdit: canUpdate(options),
      })),
    [courseId],
  );

  useEffect(() => {
    if (typeof courseId === 'number') logCourseView(courseId);
  }, [courseId]);

  if (loading && !data) return <PageContainer><Spinner /></PageContainer>;
  if (error || !data?.course) return <PageContainer>
    <ErrorAlert error={error ?? { message: 'Kursus tidak ditemukan atau Anda tidak terdaftar.' }} /><Link to="/my/courses">← Kembali ke Kursus saya</Link>
  </PageContainer>;

  const { course, sections } = data;
  const isTeacher =
    user?.isAdmin ||
    user?.teacherCourseIds?.includes(courseId) ||
    (isDosen && (String(course?.instructor_id) === String(user?.id) || typeof courseId === 'string'));
  const canEdit = user?.isAdmin || data.canEdit;
  const base = '/course/' + courseId;
  const editMode = canEdit && pathname === base;
  const tabs = [{ to: base, label: 'Kursus', end: true }, { to: base + '/participants', label: 'Peserta' }, { to: base + '/grades', label: 'Nilai' }];
  const canUseAi = isTeacher && isDosen;
  if (canUseAi) tabs.push({ to: base + '/ai', label: 'Generator AI' });
  const showIndex = pathname === base;

  return (
    <PageContainer>
      <nav className="mb-3 text-sm text-muted" aria-label="Breadcrumb">
        <Link to="/my/courses">Kursus saya</Link>
        {' / '}
        {trail.length ? <Link to={base}>{course.shortname}</Link> : <span aria-current="page">{course.shortname}</span>}
        {trail.map((item, index) => {
          const last = index === trail.length - 1;
          return (
            <Fragment key={`${index}-${item.label}`}>
              {' / '}
              {item.to && !last ? <Link to={item.to}>{item.label}</Link> : <span aria-current={last ? 'page' : undefined}>{item.label}</span>}
            </Fragment>
          );
        })}
      </nav>
      <h1 className="moodle-h1 mb-4">{course.fullname}</h1>
      <nav className="tabs" aria-label="Navigasi kursus">
        {tabs.map((tab) => (
          <NavLink key={tab.to} to={tab.to} end={tab.end} className="tabs__link">
            {tab.label}
          </NavLink>
        ))}
      </nav>
      {showIndex && (
        <details className="mb-4 rounded-lg border border-line bg-white p-3">
          <summary className="cursor-pointer font-semibold">Indeks kursus</summary>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {sections.map((section) => (
              <div key={section.id}>
                <Link to={base + '#section-' + section.section} className="font-semibold">
                  {section.name}
                </Link>
                <ul className="mt-1 text-sm">
                  {(section.modules ?? [])
                    .filter((module) => module.modname !== 'label' && module.uservisible !== false)
                    .map((module) => (
                      <li key={module.id}>
                        <Link to={base + '/mod/' + module.id}>{module.name}</Link>
                      </li>
                    ))}
                </ul>
              </div>
            ))}
          </div>
        </details>
      )}
      <ErrorBoundary>
        <Outlet context={{ course, sections, isTeacher, canEdit, editMode, reload, setTrail }} />
      </ErrorBoundary>
    </PageContainer>
  );
}
