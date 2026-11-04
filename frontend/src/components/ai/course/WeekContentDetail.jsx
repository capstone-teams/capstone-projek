import { useState } from 'react';
import { regenerateContent } from '../../../services/courseService';
import { Alert, Badge, Card } from '../../ui';
import InstructionModal from '../InstructionModal';

export default function WeekContentDetail({ week, course, canRegenerate, onStarted }) {
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
