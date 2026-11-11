import { Link } from 'react-router-dom';
import { Alert, Badge } from '../../ui';

/**
 * Panel verifikasi read-back struktur kursus dari Moodle (FE-13.2).
 * Ditampilkan setelah eksekusi selesai untuk memastikan struktur di Moodle
 * cocok persis dengan course plan (jumlah, keterurutan, dan penamaan section).
 */
export default function ExecutionReadbackCard({ readback, verificationUrl = null }) {
  if (!readback || !readback.checked) {
    if (readback?.error) {
      return (
        <div id="execution-readback">
          <Alert tone="warning" title="Pemeriksaan Read-Back Moodle Gagal">
            Sistem belum dapat memverifikasi struktur di Moodle: {readback.error}
          </Alert>
        </div>
      );
    }
    return null;
  }

  const {
    matches,
    expected_sections = 16,
    actual_sections = 0,
    ordered = true,
    missing_weeks = [],
    mismatched_weeks = [],
  } = readback;

  return (
    <div id="execution-readback" className="rounded-lg border border-line bg-surface p-4 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm text-ink">
            Verifikasi Read-Back Struktur Moodle
          </span>
          <Badge tone={matches ? 'success' : 'danger'}>
            {matches ? 'Struktur Sesuai' : 'Ada Ketidaksesuaian'}
          </Badge>
        </div>
        <span className="text-xs text-muted">
          Cek Cepat Kerangka Section (Step 6 Verifikasi mengecek seluruh activity &amp; perbaikan)
        </span>
      </div>

      {matches ? (
        <Alert tone="success">
          Seluruh <strong>{actual_sections} section mingguan</strong> pada kursus Moodle telah diverifikasi sesuai dengan rencana pembelajaran dan tersusun secara berurutan.
        </Alert>
      ) : (
        <Alert tone="danger" title="Struktur Moodle Belum Sesuai Sepenuhnya">
          <div className="text-xs space-y-2 mt-1">
            <p className="m-0">
              Ditemukan ketidaksesuaian antara struktur Moodle aktual dengan rencana pembelajaran:
            </p>
            <ul className="list-disc pl-4 space-y-0.5">
              <li>
                Jumlah section: ditemukan <strong>{actual_sections}</strong> dari <strong>{expected_sections}</strong> yang diharapkan.
              </li>
              {!ordered && (
                <li>
                  Urutan section di Moodle tidak berurutan secara teratur.
                </li>
              )}
              {missing_weeks.length > 0 && (
                <li>
                  Minggu yang belum ditemukan di Moodle: <strong>Minggu {missing_weeks.join(', ')}</strong>.
                </li>
              )}
              {mismatched_weeks.length > 0 && (
                <li>
                  Minggu dengan nama tidak cocok: <strong>Minggu {mismatched_weeks.join(', ')}</strong>.
                </li>
              )}
            </ul>
            {(mismatched_weeks.length > 0 || !ordered) && (
              <p className="m-0 text-ink">
                Ketidakcocokan ini biasanya terjadi jika nama/urutan section di Moodle berbeda karakter atau berasal dari struktur kursus sebelumnya.
                {verificationUrl && (
                  <>
                    {' '}
                    <Link to={verificationUrl} relative="path" className="font-semibold underline">
                      Lihat detail perbedaan &amp; perbaikan di Tab Verifikasi →
                    </Link>
                  </>
                )}
              </p>
            )}
          </div>
        </Alert>
      )}

      {/* Rincian Parameter Pemeriksaan */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-xs">
        <div className="rounded border border-line bg-surface-subtle p-2">
          <span className="text-muted block">Section Diharapkan</span>
          <span className="font-semibold text-ink">{expected_sections} Section</span>
        </div>
        <div className="rounded border border-line bg-surface-subtle p-2">
          <span className="text-muted block">Section Terdeteksi</span>
          <span className={`font-semibold ${actual_sections === expected_sections ? 'text-success' : 'text-danger'}`}>
            {actual_sections} Section
          </span>
        </div>
        <div className="rounded border border-line bg-surface-subtle p-2">
          <span className="text-muted block">Status Urutan</span>
          <span className={`font-semibold ${ordered ? 'text-success' : 'text-danger'}`}>
            {ordered ? 'Terurut (1–16)' : 'Tidak Terurut'}
          </span>
        </div>
        <div className="rounded border border-line bg-surface-subtle p-2">
          <span className="text-muted block">Kesesuaian Total</span>
          <span className={`font-semibold ${matches ? 'text-success' : 'text-danger'}`}>
            {matches ? '100% Sesuai' : 'Perlu Penyelarasan'}
          </span>
        </div>
      </div>
    </div>
  );
}
