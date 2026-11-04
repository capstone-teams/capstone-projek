import { useState } from 'react';
import { generateContent, getPlan } from '../../../services/courseService';
import { nullOn404 } from '../../../services/apiClient';
import { useAction, useApi } from '../../../hooks/useApi';
import { Alert, Card, ErrorAlert } from '../../ui';

export default function ContentGeneratePanel({ course, hasContent, onStarted }) {
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
