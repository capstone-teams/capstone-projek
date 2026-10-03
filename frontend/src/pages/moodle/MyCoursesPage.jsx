import { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useApi } from '../../hooks/useApi';
import { getCoursesByClassification } from '../../services/moodle/moodleApi';
import { PageContainer } from '../../components/MoodleLayout';
import { EmptyState, ErrorAlert, Spinner } from '../../components/ui';
import CourseCard from '../../components/moodle/CourseCard';

const FILTERS = [
  { value: 'all', label: 'Semua' },
  { value: 'inprogress', label: 'Sedang berjalan' },
  { value: 'future', label: 'Akan datang' },
  { value: 'past', label: 'Lampau' },
];

export default function MyCoursesPage() {
  const { user } = useAuth();
  const [classification, setClassification] = useState('all');
  const [query, setQuery] = useState('');
  const { data, error, loading } = useApi(() => getCoursesByClassification(classification), [classification]);
  const teacherIds = new Set(user.teacherCourseIds);

  const q = query.trim().toLowerCase();
  const courses = (data ?? []).filter((c) => !q || `${c.fullname} ${c.shortname}`.toLowerCase().includes(q));

  return (
    <PageContainer>
      <h1 className="moodle-h1 mb-6">Kursus saya</h1>
      <section className="rounded-lg border border-line-subtle bg-white p-4 md:p-5">
        <h2 className="mb-4 text-lg">Ikhtisar kursus</h2>
        <div className="mb-5 flex flex-wrap gap-2">
          <select className="!w-auto" value={classification} onChange={(e) => setClassification(e.target.value)} aria-label="Filter kursus">
            {FILTERS.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </select>
          <input className="!w-full sm:!w-64" type="search" placeholder="Cari" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Cari kursus" />
        </div>

        <ErrorAlert error={error} />
        {loading && !data ? (
          <Spinner />
        ) : courses.length === 0 ? (
          <EmptyState title="Tidak ada kursus.">{q ? 'Tidak ada kursus yang cocok dengan pencarian.' : 'Tidak ada kursus pada filter ini.'}</EmptyState>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {courses.map((c) => (
              <CourseCard key={c.id} course={c} isTeacher={teacherIds.has(c.id)} />
            ))}
          </div>
        )}
      </section>
    </PageContainer>
  );
}
