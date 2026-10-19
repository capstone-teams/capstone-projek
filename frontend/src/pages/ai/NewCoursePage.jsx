import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { listRps } from '../../services/rpsService';
import { createCourse } from '../../services/courseService';
import { useAction, useApi } from '../../hooks/useApi';
import { Card, EmptyState, ErrorAlert, Field, PageHeader, Spinner } from '../../components/ui';
import ActivityConfigFields from '../../components/ActivityConfigFields';

export default function NewCoursePage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { data, error, loading } = useApi(listRps);
  const processed = (data?.items ?? []).filter((r) => r.status === 'processed');

  const [form, setForm] = useState({
    rps_id: params.get('rps') ?? '',
    moodle_course_id: '',
    additional_prompt: '',
    activity_configuration: { learning_material: true, assignment: true, quiz: false },
  });
  const create = useAction(createCourse);

  const rpsId = form.rps_id || processed[0]?.id || '';
  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    const res = await create.run({ ...form, rps_id: rpsId }).catch(() => null);
    if (res) navigate(`/ai/courses/${res.id}`);
  };

  return (
    <>
      <PageHeader title="Course baru" subtitle="Buat generation project dari RPS yang sudah diproses." />
      <Card>
        <ErrorAlert error={error} />
        {loading && !data ? (
          <Spinner />
        ) : processed.length === 0 ? (
          <EmptyState
            title="Belum ada RPS yang siap."
            action={
              <Link to="/ai/rps" className="btn btn--primary">
                Unggah RPS
              </Link>
            }
          >
            Unggah dan proses RPS terlebih dahulu.
          </EmptyState>
        ) : (
          <form className="form" onSubmit={onSubmit}>
            <ErrorAlert error={create.error} onClose={create.clearError} />

            <Field label="RPS">
              <select value={rpsId} onChange={update('rps_id')} required>
                {processed.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.filename}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="ID course Moodle" hint="Course tujuan di Moodle ITK. Kosongkan bila backend yang membuat course baru.">
              <input value={form.moodle_course_id} onChange={update('moodle_course_id')} placeholder="mis. IF2105-A" />
            </Field>

            <Field label="Prompt tambahan" hint="Instruksi khusus untuk agent, mis. konteks contoh kasus atau penekanan materi.">
              <textarea rows={4} value={form.additional_prompt} onChange={update('additional_prompt')} />
            </Field>

            <ActivityConfigFields
              value={form.activity_configuration}
              onChange={(activity_configuration) => setForm((f) => ({ ...f, activity_configuration }))}
            />

            <div className="form__actions">
              <Link to="/ai" className="btn btn--ghost">
                Batal
              </Link>
              <button type="submit" className="btn btn--primary" disabled={create.pending}>
                {create.pending ? 'Membuat…' : 'Buat course'}
              </button>
            </div>
          </form>
        )}
      </Card>
    </>
  );
}
