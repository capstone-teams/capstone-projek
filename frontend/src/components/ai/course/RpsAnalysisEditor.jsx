import { useState } from 'react';
import { Card, ErrorAlert, Field } from '../../ui';

/**
 * Editor koreksi hasil analisis RPS (design-api §6.7).
 *
 * Data yang diedit adalah RPS Structured Data apa adanya — bentuk yang sama
 * dengan response `GET /rps/{id}/analysis` dan yang dibaca agent saat menyusun
 * rencana serta konten. Editor menampilkannya sebagai JSON tersimpan supaya
 * tidak ada field kontrak yang hilang saat disunting; validasi akhir tetap di
 * server (`extra="forbid"`), dan pesan 422-nya ditampilkan lewat `error`.
 */
export default function RpsAnalysisEditor({ data, onSave, onCancel, saving, error }) {
  const [text, setText] = useState(() => JSON.stringify(data, null, 2));
  const [parseError, setParseError] = useState(null);

  const submit = async (event) => {
    event.preventDefault();
    let parsed;
    try {
      parsed = JSON.parse(text);
    } catch (e) {
      setParseError(`JSON tidak valid: ${e.message}`);
      return;
    }
    setParseError(null);
    await onSave(parsed);
  };

  return (
    <Card title="Edit hasil analisis RPS">
      <p className="mb-3 text-sm text-muted">
        Data ini dipakai agent untuk menyusun rencana mingguan dan konten. Koreksi bagian yang salah
        (nama mata kuliah, CPL/CPMK, topik minggu, penilaian), lalu simpan. Model tidak dipanggil
        ulang dan hasil analisis sebelumnya tidak hilang selama belum disimpan.
      </p>
      <form className="form" onSubmit={submit} noValidate>
        <ErrorAlert error={error} />
        <Field
          label="RPS Structured Data (JSON)"
          hint="Ikuti struktur yang tampil: course, cpl, cpmk, sub_cpmk, topics, weeks, assessments, references."
          error={parseError}
          errorId="rps-analysis-json-error"
        >
          <textarea
            rows={22}
            value={text}
            onChange={(event) => setText(event.target.value)}
            spellCheck={false}
            autoFocus
            aria-invalid={parseError ? 'true' : undefined}
            aria-describedby={parseError ? 'rps-analysis-json-error' : undefined}
            className={`font-mono text-xs ${parseError ? 'border-danger' : ''}`}
          />
        </Field>
        <div className="form__actions">
          <button type="button" className="btn btn--ghost" onClick={onCancel} disabled={saving}>
            Batal
          </button>
          <button type="submit" className="btn btn--primary" disabled={saving}>
            {saving ? 'Menyimpan…' : 'Simpan perubahan'}
          </button>
        </div>
      </form>
    </Card>
  );
}
