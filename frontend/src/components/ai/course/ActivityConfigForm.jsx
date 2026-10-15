import { useState } from 'react';
import { updateActivityConfiguration } from '../../../services/courseService';
import { useAction } from '../../../hooks/useApi';
import { Alert, ErrorAlert } from '../../ui';
import ActivityConfigFields from '../ActivityConfigFields';
import { isBusy } from '../../../utils/workflow';

const LOCKED_CONFIG = ['APPROVED', 'EXECUTING', 'EXECUTED', 'VERIFYING', 'COMPLETED'];

export default function ActivityConfigForm({ course, onSaved }) {
  const [value, setValue] = useState(course.activity_configuration);
  const [saved, setSaved] = useState(false);
  const save = useAction((cfg) => updateActivityConfiguration(course.id, cfg));
  const locked = LOCKED_CONFIG.includes(course.status) || isBusy(course.status);
  const dirty = JSON.stringify(value) !== JSON.stringify(course.activity_configuration);

  return (
    <div className="form">
      <ErrorAlert error={save.error} onClose={save.clearError} />
      {saved && !dirty && <Alert tone="success">Konfigurasi tersimpan. Berlaku untuk konten yang digenerate berikutnya.</Alert>}
      <ActivityConfigFields
        value={value}
        disabled={locked}
        onChange={(v) => {
          setSaved(false);
          setValue(v);
        }}
      />
      {locked ? (
        <p className="muted">Konfigurasi terkunci pada tahap ini.</p>
      ) : (
        dirty && (
          <div className="form__actions">
            <button type="button" className="btn btn--ghost" onClick={() => setValue(course.activity_configuration)}>
              Batal
            </button>
            <button
              type="button"
              className="btn btn--primary"
              disabled={save.pending}
              onClick={() =>
                save
                  .run(value)
                  .then(() => {
                    setSaved(true);
                    return onSaved();
                  })
                  .catch(() => {})
              }
            >
              Simpan
            </button>
          </div>
        )
      )}
    </div>
  );
}
