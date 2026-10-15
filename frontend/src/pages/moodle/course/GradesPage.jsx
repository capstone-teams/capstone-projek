import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { useAuth } from '../../../hooks/useAuth';
import { useApi } from '../../../hooks/useApi';
import { getGradeItems } from '../../../services/moodle/moodleApi';
import { EmptyState, ErrorAlert, Spinner } from '../../../components/ui';
import ActivityIcon from '../../../components/moodle/ActivityIcon';
import MoodleHtml from '../../../components/moodle/MoodleHtml';

const itemLabel = (item) => (item.itemtype === 'course' ? 'Total kursus' : item.itemname ?? '-');
const range = (item) => `${Number(item.grademin ?? 0)}–${Number(item.grademax ?? 100)}`;

/** Laporan nilai mahasiswa (seperti grade/report/user). */
function UserReport({ usergrade }) {
  return (
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
          {usergrade.gradeitems.map((item) => {
            const total = item.itemtype === 'course';
            return (
              <tr key={item.id} className={total ? 'bg-surface font-bold' : ''}>
                <td>
                  <div className="flex items-center gap-2">
                    {item.itemmodule && <ActivityIcon modname={item.itemmodule} size="xs" />}
                    {itemLabel(item)}
                  </div>
                </td>
                <td>{item.gradeformatted || '-'}</td>
                <td>{range(item)}</td>
                <td>{item.percentageformatted || '-'}</td>
                <td>{item.feedback ? <MoodleHtml html={item.feedback} /> : '-'}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** Rekap nilai semua mahasiswa (mirip grader report) untuk dosen. */
function GraderReport({ usergrades }) {
  const columns = usergrades[0]?.gradeitems ?? [];
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>Mahasiswa</th>
            {columns.map((c) => (
              <th key={c.id} className={c.itemtype === 'course' ? 'bg-surface' : ''}>
                {itemLabel(c)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {usergrades.map((ug) => (
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
  );
}

export default function GradesPage() {
  const { course, isTeacher } = useMoodleCourse();
  const { user } = useAuth();
  const { data, error, loading } = useApi(() => getGradeItems(course.id, isTeacher ? 0 : user.id), [course.id, isTeacher]);

  if (loading && !data) return <Spinner />;
  if (error) return <ErrorAlert error={error} />;
  if (!data?.length) return <EmptyState title="Belum ada nilai." />;

  return (
    <div>
      <h2 className="mb-3 text-xl">{isTeacher ? 'Rekap nilai mahasiswa' : 'Laporan nilai'}</h2>
      {isTeacher ? <GraderReport usergrades={data} /> : <UserReport usergrade={data[0]} />}
    </div>
  );
}
