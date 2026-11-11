import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getInstructorSetup, updateInstructorSetup } from '../../../services/instructorService';
import { PLAN_STATUS } from '../../../services/coursePlanService';
import { useApi } from '../../../hooks/useApi';
import { plannedActivityTypesOf } from '../../../utils/coursePlan';
import { Badge } from '../../ui';
import { ACTIVITY_OPTIONS, DEFAULT_ACTIVITY_CONFIGURATION } from '../instructorSetupConstants';

const ACTIVITY_LABEL_BY_KEY = Object.fromEntries(ACTIVITY_OPTIONS.map((opt) => [opt.key, opt.label]));

/**
 * Panel ringkas konfigurasi jenis aktivitas AI (`learning_material`, `learning_resource`, `assignment`, `quiz`).
 * - Mode `edit`: memungkinkan dosen mengaktifkan/mematikan jenis aktivitas langsung sebelum menyusun Course Plan.
 * - Mode `readonly`: menampilkan jenis aktivitas yang aktif pada Course Plan beserta tautan ke Profil dosen.
 */
export default function ActivityConfigPanel({ mode = 'edit', plan = null, onUpdated }) {
  const setupQuery = useApi(() => getInstructorSetup().catch(() => null), []);
  const setup = setupQuery.data;
  const [saving, setSaving] = useState(false);
  const [savedNotice, setSavedNotice] = useState(false);
  const [validationError, setValidationError] = useState(null);
  const [saveError, setSaveError] = useState(null);

  useEffect(() => {
    if (!savedNotice) return undefined;
    const timer = setTimeout(() => setSavedNotice(false), 3000);
    return () => clearTimeout(timer);
  }, [savedNotice]);

  const activeConfig = setup?.activity_configuration
    ? { ...DEFAULT_ACTIVITY_CONFIGURATION, ...setup.activity_configuration }
    : null;

  if (mode === 'readonly') {
    const plannedTypes = plannedActivityTypesOf(plan);
    const configuredTypes = activeConfig
      ? ACTIVITY_OPTIONS.filter((opt) => activeConfig[opt.key]).map((opt) => opt.key)
      : [];
    const displayTypes = plannedTypes.length > 0 ? plannedTypes : configuredTypes;
    if (displayTypes.length === 0) return null;

    const missingOtherTypes = ['learning_resource', 'assignment', 'quiz'].some((key) => !displayTypes.includes(key));

    return (
      <section
        className="rounded-lg border border-line bg-surface/60 p-3 text-xs"
        aria-label="Ringkasan konfigurasi aktivitas rencana"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-semibold text-ink">Jenis konten aktif pada rencana ini:</span>
            {displayTypes.map((key) => (
              <Badge key={key} tone="neutral">{ACTIVITY_LABEL_BY_KEY[key] ?? key}</Badge>
            ))}
          </div>
          <Link to="/user/profile" className="font-medium text-primary underline">
            Atur di Profil dosen
          </Link>
        </div>
        {missingOtherTypes && (
          <p className="m-0 mt-1.5 text-muted">
            Jenis konten yang di-generate dikunci saat Course Plan disetujui. Untuk mengaktifkan Tugas, Sumber Referensi, atau Kuis pada penyusunan rencana berikutnya, ubah konfigurasi di{' '}
            <Link to="/user/profile" className="font-medium text-primary underline">Profil dosen</Link>{' '}
            atau di tab Rencana sebelum rencana baru disusun.
          </p>
        )}
      </section>
    );
  }

  if (!activeConfig) return null;

  const handleToggle = async (key, checked) => {
    const nextConfig = { ...activeConfig, [key]: checked };
    if (!Object.values(nextConfig).some(Boolean)) {
      setValidationError('Minimal satu jenis aktivitas pembelajaran harus diaktifkan.');
      return;
    }
    setValidationError(null);
    setSaveError(null);
    setSavedNotice(false);
    setSaving(true);
    try {
      const updated = await updateInstructorSetup({ activity_configuration: nextConfig });
      setupQuery.setData(updated);
      setSavedNotice(true);
      onUpdated?.(updated);
    } catch (err) {
      setSaveError(err?.message || 'Gagal menyimpan konfigurasi aktivitas.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <section
      className="mb-4 rounded-lg border border-line bg-surface/60 p-3.5"
      aria-label="Konfigurasi jenis aktivitas konten AI"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="m-0 text-sm font-semibold text-ink">Konfigurasi aktivitas pembelajaran AI</h3>
          {saving && <Badge tone="info">Menyimpan…</Badge>}
          {!saving && savedNotice && <Badge tone="success">Tersimpan</Badge>}
        </div>
        <Link to="/user/profile" className="text-xs font-medium text-primary underline">
          Pengaturan profil dosen
        </Link>
      </div>

      <p className="mt-1 mb-0 text-xs text-muted">
        Pilih jenis konten yang ingin ikut direncanakan agent saat menyusun Course Plan. Catatan: <strong>Kuis</strong> hanya dihasilkan pada minggu bertipe Kuis di RPS.
      </p>

      <div className="mt-2.5 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {ACTIVITY_OPTIONS.map((opt) => (
          <label
            key={opt.key}
            className="flex cursor-pointer items-start gap-2 rounded-md border border-line bg-white px-2.5 py-2 text-xs transition-colors hover:border-primary/60"
          >
            <input
              type="checkbox"
              name={`course_activity_${opt.key}`}
              checked={Boolean(activeConfig[opt.key])}
              disabled={saving}
              onChange={(e) => handleToggle(opt.key, e.target.checked)}
              className="mt-0.5 size-4 shrink-0 accent-primary"
            />
            <span className="min-w-0">
              <strong className="block font-semibold text-ink">{opt.label}</strong>
              <span className="text-[11px] text-muted">{opt.hint}</span>
            </span>
          </label>
        ))}
      </div>

      {plan?.status === PLAN_STATUS.DRAFT && (
        <p className="m-0 mt-2 text-xs text-muted">
          Rencana saat ini berstatus Draft. Jika Anda mengubah pilihan setelah rencana ini dibuat, klik <strong>Tolak dengan catatan</strong> lalu <strong>Regenerasi rencana</strong> agar pilihan baru diterapkan.
        </p>
      )}
      {plan?.status === PLAN_STATUS.REJECTED && (
        <p className="m-0 mt-2 text-xs text-muted">
          Sesuaikan pilihan aktivitas di atas sebelum mengklik <strong>Regenerasi rencana</strong>.
        </p>
      )}
      {(validationError || saveError) && (
        <p className="m-0 mt-2 text-xs font-semibold text-danger">
          {validationError || saveError}
        </p>
      )}
    </section>
  );
}
