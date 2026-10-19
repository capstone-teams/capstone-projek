import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { RPS_ACCEPTED_TYPES, RPS_MAX_SIZE_MB, listRps, processRps, uploadRps } from '../../services/rpsService';
import { useAction, useApi } from '../../hooks/useApi';
import { usePolling } from '../../hooks/usePolling';
import { Alert, Badge, Card, EmptyState, ErrorAlert, PageHeader, Spinner } from '../../components/ui';
import { RPS_STATUS_LABELS } from '../../utils/workflow';
import { formatDateTime, formatFileSize } from '../../utils/format';

const RPS_TONES = { processed: 'success', failed: 'danger', uploaded: 'neutral' };

function UploadForm({ onDone }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [localError, setLocalError] = useState('');
  const upload = useAction(async (f) => {
    const rps = await uploadRps(f);
    // Langsung minta backend memproses RPS (async, design-api.md §6.3).
    await processRps(rps.id);
    return rps;
  });

  const pick = (e) => {
    const f = e.target.files?.[0] ?? null;
    setLocalError('');
    upload.clearError();
    if (f && !/\.(pdf|docx)$/i.test(f.name)) setLocalError('Format file harus PDF atau DOCX.');
    else if (f && f.size > RPS_MAX_SIZE_MB * 1024 * 1024) setLocalError(`Ukuran file maksimal ${RPS_MAX_SIZE_MB} MB.`);
    setFile(f);
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!file || localError) return;
    const rps = await upload.run(file).catch(() => null);
    if (rps) {
      setFile(null);
      if (inputRef.current) inputRef.current.value = '';
      onDone();
    }
  };

  return (
    <form className="upload" onSubmit={onSubmit}>
      <ErrorAlert error={upload.error} onClose={upload.clearError} />
      {localError && <Alert>{localError}</Alert>}
      <label className="dropzone">
        <input ref={inputRef} type="file" accept={RPS_ACCEPTED_TYPES} onChange={pick} />
        <span className="dropzone__title">{file ? file.name : 'Pilih file RPS'}</span>
        <span className="muted">
          {file ? formatFileSize(file.size) : `PDF atau DOCX, maksimal ${RPS_MAX_SIZE_MB} MB`}
        </span>
      </label>
      <button type="submit" className="btn btn--primary" disabled={!file || !!localError || upload.pending}>
        {upload.pending ? 'Mengunggah…' : 'Unggah & proses'}
      </button>
    </form>
  );
}

export default function RpsPage() {
  const { data, error, loading, reload } = useApi(listRps);
  const items = data?.items ?? [];
  const processing = items.some((r) => ['uploaded', 'processing', 'analyzing'].includes(r.status));

  usePolling(() => reload({ silent: true }), 2000, processing);

  return (
    <>
      <PageHeader title="RPS" subtitle="RPS adalah sumber utama informasi akademik untuk agent." />
      <div className="grid grid--sidebar">
        <Card title="Unggah RPS baru">
          <UploadForm onDone={() => reload({ silent: true })} />
        </Card>

        <Card title="Daftar RPS">
          <ErrorAlert error={error} />
          {loading && !data ? (
            <Spinner />
          ) : items.length === 0 ? (
            <EmptyState title="Belum ada RPS." />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>File</th>
                    <th>Ukuran</th>
                    <th>Diunggah</th>
                    <th>Status</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {items.map((r) => (
                    <tr key={r.id}>
                      <td>{r.filename}</td>
                      <td>{formatFileSize(r.size)}</td>
                      <td>{formatDateTime(r.created_at)}</td>
                      <td>
                        <Badge tone={RPS_TONES[r.status] ?? 'info'}>{RPS_STATUS_LABELS[r.status] ?? r.status}</Badge>
                      </td>
                      <td className="table__actions">
                        {r.status === 'processed' && (
                          <>
                            <Link to={`/ai/rps/${r.id}`} className="btn btn--ghost btn--sm">
                              Analisis
                            </Link>
                            <Link to={`/ai/courses/new?rps=${r.id}`} className="btn btn--sm">
                              Buat course
                            </Link>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
