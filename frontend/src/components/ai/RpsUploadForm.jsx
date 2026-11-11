import { useId, useRef, useState } from 'react';
import {
  RPS_ACCEPTED_TYPES,
  RPS_MAX_SIZE_LABEL,
  processRps,
  uploadRps,
  validateRpsFile,
} from '../../services/rpsService';
import { Alert, ErrorAlert, ProgressBar } from '../ui';
import { formatFileSize } from '../../utils/format';

const STAGE_LABEL = { uploading: 'Mengunggah file…', processing: 'Memulai pemrosesan…' };

/**
 * Pilih file RPS (klik atau seret), validasi di klien, unggah dengan progres, lalu mulai pemrosesan.
 * onUploaded({ rps, processing, error }) dipanggil setelah file tersimpan di server — juga bila
 * pemrosesan gagal dimulai (error berisi penyebabnya) agar RPS tetap tampil di daftar.
 */
export default function RpsUploadForm({ onUploaded, defaultAutopilot = true }) {
  const inputRef = useRef(null);
  // Mode otomatis: RPS → course plan → konten seluruh minggu tanpa klik per tahap; publikasi ke Moodle tetap
  // menunggu satu review akhir dosen.
  const [autopilot, setAutopilot] = useState(defaultAutopilot);
  const errorId = useId();
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [stage, setStage] = useState(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const busy = stage !== null;

  const choose = (next) => {
    setError(null);
    setNotice(null);
    setFile(next);
    setFileError(next ? validateRpsFile(next) : null);
  };

  const reset = () => {
    setFile(null);
    setFileError(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const submit = async (event) => {
    event.preventDefault();
    const invalid = validateRpsFile(file);
    if (invalid) {
      setFileError(invalid);
      return;
    }
    setError(null);
    setNotice(null);
    setProgress(0);
    setStage('uploading');
    let rps;
    try {
      rps = await uploadRps(file, { onProgress: setProgress });
    } catch (e) {
      setError(e);
      setStage(null);
      return;
    }
    setStage('processing');
    let processing = null;
    let processError = null;
    try {
      processing = await processRps(rps.id, { autopilot });
    } catch (e) {
      processError = e;
    }
    setStage(null);
    reset();
    if (processError) {
      setError({ code: processError.code, message: `RPS terunggah, tetapi pemrosesan gagal dimulai: ${processError.message}` });
    }
    else if (rps.deduplicated) setNotice('File yang sama sudah pernah diunggah; RPS yang ada dipakai kembali.');
    else if (processing?.reused) setNotice('RPS ini sudah pernah diproses; hasil sebelumnya dipakai kembali.');
    else if (autopilot) setNotice('RPS diproses otomatis sampai materi mingguan siap ditinjau. Anda dapat meninggalkan halaman ini.');
    onUploaded?.({ rps, processing, error: processError });
  };

  const onDrop = (event) => {
    event.preventDefault();
    setDragging(false);
    if (!busy) choose(event.dataTransfer.files?.[0] ?? null);
  };

  return (
    <form className="upload" onSubmit={submit} noValidate>
      <ErrorAlert error={error} onClose={() => setError(null)} />
      {notice && <Alert tone="info">{notice}</Alert>}

      <label
        className={`dropzone ${dragging ? 'border-primary bg-primary-light' : ''} ${fileError ? 'border-danger' : ''}`}
        onDragOver={(event) => { event.preventDefault(); if (!busy) setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept={RPS_ACCEPTED_TYPES}
          disabled={busy}
          aria-invalid={fileError ? 'true' : undefined}
          aria-describedby={fileError ? errorId : undefined}
          onChange={(event) => choose(event.target.files?.[0] ?? null)}
        />
        <span className="dropzone__title">{file ? file.name : 'Pilih atau seret file RPS ke sini'}</span>
        <span className="muted">
          {file ? formatFileSize(file.size) : `PDF, maksimal ${RPS_MAX_SIZE_LABEL}`}
        </span>
      </label>

      {fileError && (
        <p id={errorId} role="alert" className="text-sm font-semibold text-danger">
          {fileError}
        </p>
      )}

      {busy && (
        <ProgressBar
          label={STAGE_LABEL[stage]}
          completed={stage === 'uploading' ? progress : 100}
          total={100}
          hideCount
        />
      )}

      <label className="flex items-start gap-2 text-sm">
        <input
          type="checkbox"
          className="mt-0.5"
          checked={autopilot}
          disabled={busy}
          onChange={(event) => setAutopilot(event.target.checked)}
        />
        <span>
          <strong>Generate otomatis sampai materi siap ditinjau</strong>
          <span className="block text-muted">
            Analisis RPS, rencana mingguan, dan isi materi dibuat berurutan tanpa perlu menyetujui tiap tahap. Materi
            dikirim ke Moodle setelah Anda meninjau dan menyetujuinya.
          </span>
        </span>
      </label>

      <button type="submit" className="btn btn--primary" disabled={!file || !!fileError || busy}>
        {busy ? STAGE_LABEL[stage] : 'Unggah & proses'}
      </button>
    </form>
  );
}
