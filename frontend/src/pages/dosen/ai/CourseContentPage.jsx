import { useSearchParams } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { getContent } from '../../../services/courseService';
import { useApi } from '../../../hooks/useApi';
import { Badge, Card, EmptyState, ErrorAlert, ProgressBar, Spinner } from '../../../components/ui';
import ContentGeneratePanel from '../../../components/ai/course/ContentGeneratePanel';
import WeekContentDetail from '../../../components/ai/course/WeekContentDetail';

const CAN_GENERATE = ['PLAN_APPROVED', 'WAITING_CONTENT_REVIEW', 'CONTENT_REJECTED'];
const CAN_REGENERATE = ['WAITING_CONTENT_REVIEW', 'CONTENT_REJECTED'];
const BEFORE_PLAN_APPROVED = ['CREATED', 'PLANNING', 'WAITING_PLAN_REVIEW'];

export default function CourseContentPage() {
  const { course, version, refresh } = useCourse();
  const [params, setParams] = useSearchParams();
  const content = useApi(() => getContent(course.id), [course.id, version]);
  const weeks = content.data?.weeks ?? [];

  if (BEFORE_PLAN_APPROVED.includes(course.status)) {
    return (
      <Card>
        <EmptyState title="Rencana belum disetujui.">Konten mingguan dapat digenerate setelah rencana course disetujui.</EmptyState>
      </Card>
    );
  }

  const selectedWeek = Number(params.get('week')) || weeks[0]?.week;
  const selected = weeks.find((w) => w.week === selectedWeek);
  const generating = course.status === 'GENERATING_CONTENT' || course.status === 'VALIDATING';

  return (
    <div className="stack">
      {generating && (
        <Card>
          {course.status === 'VALIDATING' ? (
            <Spinner label="Memvalidasi konten terhadap RPS…" />
          ) : (
            course.progress && (
              <ProgressBar completed={course.progress.completed} total={course.progress.total} label={`Generate konten · ${course.stage ?? ''}`} />
            )
          )}
        </Card>
      )}

      {CAN_GENERATE.includes(course.status) && <ContentGeneratePanel course={course} hasContent={weeks.length > 0} onStarted={refresh} />}

      <ErrorAlert error={content.error} />
      {content.loading && !content.data ? (
        <Spinner />
      ) : weeks.length === 0 ? (
        !generating && (
          <Card>
            <EmptyState title="Belum ada konten." />
          </Card>
        )
      ) : (
        <div className="grid grid--sidebar">
          <Card title="Minggu">
            <ul className="week-nav">
              {weeks.map((w) => (
                <li key={w.week}>
                  <button
                    type="button"
                    className={`week-nav__btn ${w.week === selectedWeek ? 'week-nav__btn--active' : ''}`}
                    onClick={() => setParams({ week: String(w.week) }, { replace: true })}
                  >
                    <span className="week-nav__num">{w.week}</span>
                    <span className="week-nav__topic">{w.topic}</span>
                    {w.revision > 0 && <Badge tone="info">r{w.revision}</Badge>}
                  </button>
                </li>
              ))}
            </ul>
          </Card>
          {selected && (
            <WeekContentDetail week={selected} course={course} canRegenerate={CAN_REGENERATE.includes(course.status)} onStarted={refresh} />
          )}
        </div>
      )}
    </div>
  );
}
