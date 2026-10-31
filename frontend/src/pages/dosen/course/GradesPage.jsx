import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { useApi } from '../../../hooks/useApi';
import { getGradeItems } from '../../../services/moodle/moodleApi';
import { EmptyState, ErrorAlert, Spinner } from '../../../components/ui';
import { gradeItemLabel } from '../../../utils/grades';

/** Rekap nilai semua mahasiswa (mirip grader report Moodle). */
export default function GradesPage() {
  const { course } = useMoodleCourse();
  // userid 0 = semua peserta.
  const { data, error, loading } = useApi(() => getGradeItems(course.id, 0), [course.id]);

  if (loading && !data) return <Spinner />;
  if (error) return <ErrorAlert error={error} />;
  if (!data?.length) return <EmptyState title="Belum ada nilai." />;

  const columns = data[0]?.gradeitems ?? [];
  return (
    <div>
      <h2 className="mb-3 text-xl">Rekap nilai mahasiswa</h2>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Mahasiswa</th>
              {columns.map((c) => (
                <th key={c.id} className={c.itemtype === 'course' ? 'bg-surface' : ''}>
                  {gradeItemLabel(c)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((ug) => (
              <tr key={ug.userid}>
                <td className="whitespace-nowrap">{ug.userfullname}</td>
                {ug.gradeitems.map((g) => (
                  <td key={g.id} className={g.itemtype === 'course' ? 'bg-surface font-bold' : ''}>
                    {g.gradeformatted || '-'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
