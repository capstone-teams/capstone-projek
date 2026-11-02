import { useState } from 'react';
import { RPS_READY } from '../../../utils/rpsStatus';
import { COURSE_API_AVAILABLE, RPS_DELETE_AVAILABLE } from '../../../services/config';
import { createCourse } from '../../../services/courseService';
import { setMoodleTarget } from '../../../services/workflowService';
import { useAction } from '../../../hooks/useApi';
import { useRpsLibrary } from '../../../hooks/useRpsLibrary';
import { Card, ErrorAlert, Field, Spinner } from '../../ui';
import ActivityConfigFields from '../ActivityConfigFields';
import RpsList from '../RpsList';
import RpsUploadForm from '../RpsUploadForm';

/** Tanpa API /courses: RPS terpilih menjadi course target workflow-nya (PUT /workflows/{id}/moodle-target). */
function CourseTargetCard({ moodleCourse, rps, onCreated }) {
  const connect = useAction(() => setMoodleTarget(rps.workflow_id, moodleCourse.id));
  return (
    <Card title="2. Hubungkan ke kursus">
      <p className="mb-3 text-muted">
        Gunakan RPS yang sudah dianalisis untuk <strong>{moodleCourse.fullname}</strong>.
      </p>
      <ErrorAlert error={connect.error} onClose={connect.clearError} />
      <button type="button" className="btn btn--primary" disabled={!rps || connect.pending} onClick={() => connect.run().then(onCreated).catch(() => {})}>
        {connect.pending ? 'Menghubungkan…' : 'Hubungkan RPS'}
      </button>
      {!rps && <p className="mt-2 text-sm text-muted">Unggah RPS dan tunggu sampai selesai dianalisis.</p>}
    </Card>
  );
}

/** Form awal saat kursus belum punya project generator: pilih/unggah RPS lalu atur aktivitas. */
export default function AiProjectStart({ moodleCourse, onCreated }) {
  // Unggah RPS (FE-08.1): validasi klien, progres, pemrosesan, dan daftar RPS milik dosen.
  const library = useRpsLibrary();
  const processed = library.items.filter((r) => RPS_READY.includes(r.status) && (COURSE_API_AVAILABLE || r.workflow_id));

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
        <div className="stack">
          <RpsUploadForm onUploaded={library.addUploaded} />
          <ErrorAlert error={library.error} />
          <ErrorAlert error={library.actionError} onClose={library.clearActionError} />
          {library.loading ? (
            <Spinner label="Memuat daftar RPS…" />
          ) : (
            !library.error && (
              <RpsList
                items={library.items}
                progress={library.progress}
                highlightId={library.highlightId}
                busyId={library.busyId}
                onProcess={library.process}
                onReanalyze={library.reanalyze}
                onHide={RPS_DELETE_AVAILABLE ? library.hide : undefined}
                analysisHref={COURSE_API_AVAILABLE ? undefined : (item) => `rps?rps=${item.id}`}
                monitorHref={(item) => `workflows?workflow=${item.workflow_id}`}
              />
            )
          )}
          {processed.length > 0 && (
            <Field label="RPS untuk kursus ini" hint="Hanya RPS yang selesai diproses yang dapat dipakai generator.">
              <select value={rpsId} onChange={update('rps_id')} required>
                {processed.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.filename}
                  </option>
                ))}
              </select>
            </Field>
          )}
        </div>
      </Card>

      {!COURSE_API_AVAILABLE ? (
        <CourseTargetCard moodleCourse={moodleCourse} rps={processed.find((r) => r.id === rpsId)} onCreated={onCreated} />
      ) : (
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
      )}
    </div>
  );
}
