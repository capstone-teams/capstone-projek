import { useRef, useState } from 'react';
import { RPS_ACCEPTED_TYPES, RPS_MAX_SIZE_MB, processRps, uploadRps } from '../../services/rpsService';
import { useAction } from '../../hooks/useApi';
import { Alert, ErrorAlert } from '../ui';
import { formatFileSize } from '../../utils/format';

export default function RpsUploadForm({ onDone }) {
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
