import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { useAuth } from '../../../hooks/useAuth';
import { useApi } from '../../../hooks/useApi';
import { getGradeItems } from '../../../services/moodle/moodleApi';
import { EmptyState, ErrorAlert, Spinner } from '../../../components/ui';
import ActivityIcon from '../../../components/moodle/ActivityIcon';
import MoodleHtml from '../../../components/moodle/MoodleHtml';
import { gradeItemLabel, gradeRange } from '../../../utils/grades';

/** Laporan nilai mahasiswa sendiri (seperti grade/report/user Moodle). */
export default function GradesPage() {
  const { course } = useMoodleCourse();
  const { user } = useAuth();
  const { data, error, loading } = useApi(() => getGradeItems(course.id, user.id), [course.id, user.id]);

  if (loading && !data) return <Spinner />;
  if (error) return <ErrorAlert error={error} />;
  if (!data?.length) return <EmptyState title="Belum ada nilai." />;

  return (
    <div>
      <h2 className="mb-3 text-xl">Laporan nilai</h2>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Item penilaian</th>
              <th>Nilai</th>
              <th>Rentang</th>
              <th>Persentase</th>
              <th>Umpan balik</th>
            </tr>
          </thead>
          <tbody>
            {data[0].gradeitems.map((item) => {
              const total = item.itemtype === 'course';
              return (
                <tr key={item.id} className={total ? 'bg-surface font-bold' : ''}>
                  <td>
                    <div className="flex items-center gap-2">
                      {item.itemmodule && <ActivityIcon modname={item.itemmodule} size="xs" />}
                      {gradeItemLabel(item)}
                    </div>
                  </td>
                  <td>{item.gradeformatted || '-'}</td>
                  <td>{gradeRange(item)}</td>
                  <td>{item.percentageformatted || '-'}</td>
                  <td>{item.feedback ? <MoodleHtml html={item.feedback} /> : '-'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
