import { useState } from 'react';
import { RPS_READY } from '../../../utils/rpsStatus';
import { createCourse } from '../../../services/courseService';
import { useAction } from '../../../hooks/useApi';
import { useRpsLibrary } from '../../../hooks/useRpsLibrary';
import { Alert, Card, ErrorAlert, Field, Spinner } from '../../ui';
import ActivityConfigFields from '../ActivityConfigFields';
import RpsList from '../RpsList';
import RpsUploadForm from '../RpsUploadForm';

/** Form awal saat kursus belum punya project generator: pilih/unggah RPS lalu atur aktivitas. */
export default function AiProjectStart({ moodleCourse, onCreated }) {
  // Unggah RPS (FE-08.1): validasi klien, progres, pemrosesan, dan daftar RPS milik dosen.
  const library = useRpsLibrary();
  const processed = library.items.filter((r) => RPS_READY.includes(r.status));

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
          {library.unavailable && (
            <Alert tone="info">Daftar RPS dari server belum tersedia; yang tampil adalah RPS yang Anda unggah pada sesi ini.</Alert>
          )}
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
