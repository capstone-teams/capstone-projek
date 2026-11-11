import { useState } from 'react';
import { RPS_READY } from '../../../utils/rpsStatus';
import { RPS_DELETE_AVAILABLE } from '../../../services/config';
import { moodleCourseIdOf, setMoodleTarget } from '../../../services/workflowService';
import { useAction } from '../../../hooks/useApi';
import { useRpsLibrary } from '../../../hooks/useRpsLibrary';
import { Card, ErrorAlert, Field, Spinner } from '../../ui';
import RpsList from '../RpsList';
import RpsUploadForm from '../RpsUploadForm';

/** RPS terpilih menjadi course target workflow-nya (PUT /workflows/{id}/moodle-target). */
function CourseTargetCard({ moodleCourse, rps, onCreated }) {
  const moodleId = moodleCourseIdOf(moodleCourse);
  const connect = useAction(() => setMoodleTarget(rps.workflow_id, moodleId));
  return (
    <Card title="2. Hubungkan ke kursus">
      <p className="mb-3 text-muted">
        Gunakan RPS yang sudah dianalisis untuk <strong>{moodleCourse.fullname}</strong>.
      </p>
      <ErrorAlert error={connect.error} onClose={connect.clearError} />
      <button type="button" className="btn btn--primary" disabled={!rps || !moodleId || connect.pending} onClick={() => connect.run().then(onCreated).catch(() => {})}>
        {connect.pending ? 'Menghubungkan…' : 'Hubungkan RPS'}
      </button>
      {!moodleId && <p className="mt-2 text-sm text-muted">Kursus ini belum terhubung ke kursus Moodle.</p>}
      {moodleId && !rps && <p className="mt-2 text-sm text-muted">Unggah RPS dan tunggu sampai selesai dianalisis.</p>}
    </Card>
  );
}

/** Form awal saat kursus belum punya workflow generator: pilih/unggah RPS lalu hubungkan target kursus. */
export default function AiProjectStart({ moodleCourse, onCreated }) {
  const library = useRpsLibrary();
  const processed = library.items.filter((r) => RPS_READY.includes(r.status) && r.workflow_id);

  const [selectedRpsId, setSelectedRpsId] = useState('');
  const rpsId = selectedRpsId || processed[0]?.id || '';

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
                analysisHref={(item) => `rps?rps=${item.id}`}
                monitorHref={(item) => `workflows?workflow=${item.workflow_id}`}
              />
            )
          )}
          {processed.length > 0 && (
            <Field label="RPS untuk kursus ini" hint="Hanya RPS yang selesai diproses yang dapat dipakai generator.">
              <select value={rpsId} onChange={(e) => setSelectedRpsId(e.target.value)} required>
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

      <CourseTargetCard moodleCourse={moodleCourse} rps={processed.find((r) => r.id === rpsId)} onCreated={onCreated} />
    </div>
  );
}
