import { NavLink, Outlet } from 'react-router-dom';
import { PageContainer } from '../../components/MoodleLayout';

const LINKS = [
  { to: '/ai', label: 'Project', end: true },
  { to: '/ai/courses/new', label: 'Course baru' },
  { to: '/ai/rps', label: 'RPS' },
  { to: '/ai/profile', label: 'Preferensi mengajar' },
];

/** Area Generator Konten AI (khusus dosen): RPS -> rencana -> konten -> review -> Moodle. */
export default function AiLayout() {
  return (
    <PageContainer>
      <div className="mb-1 text-sm text-muted">Generator Konten AI</div>
      <nav className="tabs" aria-label="Navigasi Generator AI">
        {LINKS.map((l) => (
          <NavLink key={l.to} to={l.to} end={l.end} className="tabs__link">
            {l.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </PageContainer>
  );
}
