import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { generateContent, getContent, getPlan, regenerateContent } from '../../../services/courseService';
import { nullOn404 } from '../../../services/apiClient';
import { useAction, useApi } from '../../../hooks/useApi';
import { Alert, Badge, Card, EmptyState, ErrorAlert, ProgressBar, Spinner } from '../../../components/ui';
import InstructionModal from '../../../components/InstructionModal';

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

      {CAN_GENERATE.includes(course.status) && <GeneratePanel course={course} hasContent={weeks.length > 0} onStarted={refresh} />}

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
            <WeekDetail week={selected} course={course} canRegenerate={CAN_REGENERATE.includes(course.status)} onStarted={refresh} />
          )}
        </div>
      )}
    </div>
  );
}

function GeneratePanel({ course, hasContent, onStarted }) {
  const plan = useApi(() => getPlan(course.id).catch(nullOn404), [course.id]);
  const [mode, setMode] = useState('all');
  const [picked, setPicked] = useState([]);
  const generate = useAction((weeks) => generateContent(course.id, weeks));
  const planWeeks = plan.data?.weeks ?? [];

  const toggle = (w) => setPicked((p) => (p.includes(w) ? p.filter((x) => x !== w) : [...p, w].sort((a, b) => a - b)));
  const submit = () => {
    const weeks = mode === 'all' ? 'all' : picked;
    generate
      .run(weeks)
      .then(() => {
        setPicked([]);
        return onStarted();
      })
      .catch(() => {});
  };

  return (
    <Card title={hasContent ? 'Generate ulang konten' : 'Generate konten'}>
      <ErrorAlert error={generate.error} onClose={generate.clearError} />
      {course.status === 'CONTENT_REJECTED' && (
        <Alert tone="warning">Konten ditolak saat review. Generate ulang minggu yang perlu diperbaiki.</Alert>
      )}
      <div className="segmented" role="radiogroup" aria-label="Cakupan minggu">
        <label>
          <input type="radio" name="mode" checked={mode === 'all'} onChange={() => setMode('all')} /> Semua minggu
        </label>
        <label>
          <input type="radio" name="mode" checked={mode === 'some'} onChange={() => setMode('some')} /> Pilih minggu
        </label>
      </div>
      {mode === 'some' && (
        <div className="week-picker">
          {planWeeks.map((w) => (
            <label key={w.week} className={`week-picker__item ${picked.includes(w.week) ? 'is-on' : ''}`} title={w.topic}>
              <input type="checkbox" checked={picked.includes(w.week)} onChange={() => toggle(w.week)} />
              {w.week}
            </label>
          ))}
        </div>
      )}
      <div className="form__actions">
        <button
          type="button"
          className="btn btn--primary"
          disabled={generate.pending || (mode === 'some' && picked.length === 0)}
          onClick={submit}
        >
          {generate.pending ? 'Meminta…' : mode === 'all' ? 'Generate semua minggu' : `Generate ${picked.length} minggu`}
        </button>
      </div>
    </Card>
  );
}

function WeekDetail({ week, course, canRegenerate, onStarted }) {
  const [regenerating, setRegenerating] = useState(false);
  const { assignment, quiz } = week.activities;

  return (
    <Card
      title={`Minggu ${week.week}: ${week.topic}`}
      actions={
        canRegenerate && (
          <button type="button" className="btn btn--ghost" onClick={() => setRegenerating(true)}>
            Regenerasi minggu ini
          </button>
        )
      }
    >
      {week.last_instruction && <Alert tone="info" title="Instruksi regenerasi terakhir">{week.last_instruction}</Alert>}

      <h3 className="section-title">Tujuan pembelajaran</h3>
      <ul className="compact">
        {week.learning_objectives.map((o) => (
          <li key={o}>{o}</li>
        ))}
      </ul>


      {assignment && (
        <article className="activity">
          <Badge tone="info">Assignment</Badge>
          <h3>{assignment.title}</h3>
          <p>{assignment.instructions}</p>
          <small className="muted">Nilai maksimal: {assignment.max_grade}</small>
        </article>
      )}

      {quiz && (
        <article className="activity">
          <Badge tone="info">Quiz</Badge>
          <h3>{quiz.title}</h3>
          <ol>
            {quiz.questions.map((q, i) => (
              <li key={i}>
                {q.question}
                <ul className="compact">
                  {q.options.map((opt, j) => (
                    <li key={j} className={j === q.answer ? 'is-answer' : ''}>
                      {opt}
                      {j === q.answer && ' ✓'}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>
        </article>
      )}

      {week.resources.length > 0 && (
        <>
          <h3 className="section-title">Sumber belajar</h3>
          <ul className="compact">
            {week.resources.map((r) => (
              <li key={r.title}>
                {r.url ? (
                  <a href={r.url} target="_blank" rel="noreferrer">
                    {r.title}
                  </a>
                ) : (
                  r.title
                )}
              </li>
            ))}
          </ul>
        </>
      )}

      <InstructionModal
        open={regenerating}
        title={`Regenerasi minggu ${week.week}`}
        label="Instruksi perbaikan"
        placeholder="Contoh: Perjelas contoh pada bagian kedua."
        submitLabel="Regenerasi"
        onClose={() => setRegenerating(false)}
        onSubmit={(instruction) => regenerateContent(course.id, week.id, instruction).then(onStarted)}
      />
    </Card>
  );
}
