import { useEffect } from 'react';
import { Link, NavLink, Outlet, useLocation, useParams } from 'react-router-dom';
import { useAuth } from '../../../hooks/useAuth';
import { useApi } from '../../../hooks/useApi';
import { usePreference } from '../../../hooks/useAppState';
import { getAdministrationOptions, getCourse, getCourseContents, logCourseView } from '../../../services/moodle/moodleApi';
import { PageContainer } from '../../../components/layout/MoodleLayout';
import { ErrorAlert, Spinner } from '../../../components/ui';
import { EditModeToggle } from '../../../components/moodle/editing';

// Hak mengubah isi kursus (moodle/course:update) dari core_course_get_user_administration_options.
const canUpdate = (options) => options?.[0]?.options.some((o) => o.name === 'update' && o.available) ?? false;

export default function MoodleCourseLayout() {
  const params = useParams();
  const courseId = Number(params.courseId);
  const { user } = useAuth();
  const { pathname } = useLocation();
  const { data, error, loading, reload } = useApi(
    () => Promise.all([getCourse(courseId), getCourseContents(courseId), getAdministrationOptions([courseId]).catch(() => [])])
      .then(([course, sections, options]) => ({ course, sections, canEdit: canUpdate(options) })), [courseId],
  );
  const [editModePreference, setEditMode] = usePreference('course.editMode', false);
  useEffect(() => { logCourseView(courseId); }, [courseId]);
  if (loading && !data) return <PageContainer><Spinner /></PageContainer>;
  if (error || !data?.course) return <PageContainer>
    <ErrorAlert error={error ?? { message: 'Kursus tidak ditemukan atau Anda tidak terdaftar.' }} /><Link to="/my/courses">← Kembali ke Kursus saya</Link>
  </PageContainer>;
  const { course, sections } = data;
  const isTeacher = user.isAdmin || user.teacherCourseIds.includes(courseId);
  const canEdit = user.isAdmin || data.canEdit;
  // Mode edit hanya berlaku di tab Kursus untuk pengguna yang boleh mengubah kursus.
  const editMode = canEdit && editModePreference && pathname === '/course/' + courseId;
  const base = '/course/' + courseId;
  const tabs = [{ to: base, label: 'Kursus', end: true }, { to: base + '/participants', label: 'Peserta' }, { to: base + '/grades', label: 'Nilai' }];
  // Generator AI hanya untuk dosen pengampu kursus ini.
  const canUseAi = isTeacher && user.role === 'dosen';
  if (canUseAi) tabs.push({ to: base + '/ai', label: 'Generator AI' });
  const onAiTab = pathname.startsWith(base + '/ai');
  return <PageContainer>
    <nav className="mb-3 text-sm text-muted" aria-label="Breadcrumb"><Link to="/my/courses">Kursus saya</Link> / <span>{course.shortname}</span></nav>
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
      <h1 className="moodle-h1">{course.fullname}</h1>
      {canEdit && pathname === base && <EditModeToggle checked={editModePreference} onChange={setEditMode} />}
    </div>
    <nav className="tabs" aria-label="Navigasi kursus">{tabs.map((tab) => <NavLink key={tab.to} to={tab.to} end={tab.end} className="tabs__link">{tab.label}</NavLink>)}</nav>
    {!onAiTab && <details className="mb-4 rounded-lg border border-line bg-white p-3">
      <summary className="cursor-pointer font-semibold">Indeks kursus</summary>
      <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{sections.map((section) => <div key={section.id}>
        <Link to={base + '#section-' + section.section} className="font-semibold">{section.name}</Link>
        <ul className="mt-1 text-sm">{section.modules.filter((module) => module.modname !== 'label' && module.uservisible !== false).map((module) => <li key={module.id}><Link to={base + '/mod/' + module.id}>{module.name}</Link></li>)}</ul>
      </div>)}</div>
    </details>}
    <Outlet context={{ course, sections, isTeacher, canEdit, editMode, reload }} />
  </PageContainer>;
}
