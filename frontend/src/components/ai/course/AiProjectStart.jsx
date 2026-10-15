import { useState } from 'react';
import { listRps } from '../../../services/rpsService';
import { createCourse } from '../../../services/courseService';
import { useAction, useApi } from '../../../hooks/useApi';
import { usePolling } from '../../../hooks/usePolling';
import { Badge, Card, ErrorAlert, Field, Spinner } from '../../ui';
import ActivityConfigFields from '../ActivityConfigFields';
import RpsUploadForm from '../RpsUploadForm';
import { RPS_STATUS_LABELS } from '../../../utils/workflow';

const PROCESSING = ['uploaded', 'processing', 'analyzing'];

/** Form awal saat kursus belum punya project generator: pilih/unggah RPS lalu atur aktivitas. */
export default function AiProjectStart({ moodleCourse, onCreated }) {
  const rps = useApi(listRps);
  const items = rps.data?.items ?? [];
  const processed = items.filter((r) => r.status === 'processed');
  const processing = items.filter((r) => PROCESSING.includes(r.status));
  usePolling(() => rps.reload({ silent: true }), 2000, processing.length > 0);

  const [form, setForm] = useState({
    rps_id: '',
    additional_prompt: '',
    activity_configuration: { learning_material: true, assignment: true, quiz: false },
  });
  const create = useAction(createCourse);
  const rpsId = form.rps_id || processed[0]?.id || '';
  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    const res = await create
      .run({ ...form, rps_id: rpsId, moodle_course_id: String(moodleCourse.id) })
      .catch(() => null);
    if (res) onCreated();
  };

  return (
    <div className="grid grid--2">
      <Card title="1. RPS mata kuliah">
        <p className="mb-3 text-muted">RPS adalah sumber utama informasi akademik untuk agent.</p>
        <ErrorAlert error={rps.error} />
        {rps.loading && !rps.data ? (
          <Spinner />
        ) : (
          <div className="stack">
            {processing.map((r) => (
              <div key={r.id} className="list__split">
                <span>{r.filename}</span>
                <Badge tone="info">{RPS_STATUS_LABELS[r.status] ?? r.status}</Badge>
              </div>
            ))}
            {processed.length > 0 && (
              <Field label="Pilih RPS yang sudah diproses">
                <select value={rpsId} onChange={update('rps_id')} required>
                  {processed.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.filename}
                    </option>
                  ))}
                </select>
              </Field>
            )}
            <RpsUploadForm onDone={() => rps.reload({ silent: true })} />
          </div>
        )}
      </Card>

      <Card title="2. Mulai generator AI">
        <form className="form" onSubmit={onSubmit}>
          <p className="text-muted">
            Agent akan menyusun rencana dan konten mingguan untuk <strong>{moodleCourse.fullname}</strong>, lalu
            mengirimkannya ke kursus ini setelah Anda setujui.
          </p>
          <ErrorAlert error={create.error} onClose={create.clearError} />

          <Field label="Prompt tambahan" hint="Instruksi khusus untuk agent, mis. konteks contoh kasus atau penekanan materi.">
            <textarea rows={4} value={form.additional_prompt} onChange={update('additional_prompt')} />
          </Field>

          <ActivityConfigFields
            value={form.activity_configuration}
            onChange={(activity_configuration) => setForm((f) => ({ ...f, activity_configuration }))}
          />

          <div className="form__actions">
            <button type="submit" className="btn btn--primary" disabled={!rpsId || create.pending}>
              {create.pending ? 'Membuat…' : 'Mulai generator AI'}
            </button>
          </div>
          {!rpsId && <p className="text-sm text-muted">Unggah RPS terlebih dahulu untuk memulai.</p>}
        </form>
      </Card>
    </div>
  );
}
