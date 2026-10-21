import { useEffect, useState } from 'react';
import { updateProfile } from '../../services/profileService';
import { useAction } from '../../hooks/useApi';
import { Alert, ErrorAlert, Field, Spinner } from '../ui';
import {
  ACTIVITY_OPTIONS,
  DEFAULT_ACTIVITY_CONFIGURATION,
  MAX_PROMPT_LENGTH,
} from './instructorSetupConstants';

function countCharacters(text) {
  return Array.from(text || '').length;
}

function getInitialForm(initial) {
  const data = initial || {};
  return {
    teaching_style: data.teaching_style ?? '',
    expertise: data.expertise ?? '',
    delivery_preference: data.delivery_preference ?? data.content_preference ?? '',
    additional_prompt: data.additional_prompt ?? '',
    activity_configuration: {
      ...DEFAULT_ACTIVITY_CONFIGURATION,
      ...(data.activity_configuration ?? {}),
    },
    language_preference: data.language_preference ?? 'Bahasa Indonesia',
  };
}

export default function InstructorSetupForm({
  initial = {},
  loading = false,
  onSubmit,
  onSaved,
  onReset,
  onCancel,
  isSaving: externalSaving,
  error: externalError,
}) {
  const safeInitial = initial || {};
  const [form, setForm] = useState(() => getInitialForm(safeInitial));
  const [prevInitialKey, setPrevInitialKey] = useState(() => JSON.stringify(safeInitial));
  const [errors, setErrors] = useState({});
  const [saved, setSaved] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const saveAction = useAction(updateProfile);

  const currentInitialKey = JSON.stringify(safeInitial);
  if (currentInitialKey !== prevInitialKey) {
    setPrevInitialKey(currentInitialKey);
    setForm(getInitialForm(safeInitial));
    setErrors({});
    setSubmitError(null);
  }

  const isSaving = externalSaving ?? (saveAction.pending || isSubmitting);
  const currentError = externalError ?? submitError ?? saveAction.error;

  useEffect(() => {
    if (!saved) return undefined;
    const timer = setTimeout(() => {
      setSaved(false);
    }, 4000);
    return () => clearTimeout(timer);
  }, [saved]);

  const clearCurrentError = () => {
    setSubmitError(null);
    saveAction.clearError?.();
  };

  const update = (key) => (e) => {
    setSaved(false);
    const value = e.target.value;
    setForm((f) => ({ ...f, [key]: value }));
    if (errors[key]) {
      if (key === 'additional_prompt') {
        if (countCharacters(value) <= MAX_PROMPT_LENGTH) {
          setErrors((errs) => {
            const next = { ...errs };
            delete next.additional_prompt;
            return next;
          });
        }
      } else {
        setErrors((errs) => {
          const next = { ...errs };
          delete next[key];
          return next;
        });
      }
    }
  };

  const handleActivityToggle = (key) => (e) => {
    setSaved(false);
    const checked = e.target.checked;
    setForm((f) => {
      const nextConfig = { ...f.activity_configuration, [key]: checked };
      const hasAny = Object.values(nextConfig).some(Boolean);
      if (hasAny && errors.activity_configuration) {
        setErrors((errs) => {
          const next = { ...errs };
          delete next.activity_configuration;
          return next;
        });
      }
      return { ...f, activity_configuration: nextConfig };
    });
  };

  const handleReset = () => {
    setForm(getInitialForm(safeInitial));
    setErrors({});
    setSaved(false);
    clearCurrentError();
    onReset?.();
    onCancel?.();
  };

  const handleSubmit = async (e) => {
    if (e?.preventDefault) e.preventDefault();
    setSaved(false);
    setSubmitError(null);

    const validationErrors = {};
    const hasActiveActivity = Object.values(form.activity_configuration).some(Boolean);
    if (!hasActiveActivity) {
      validationErrors.activity_configuration = 'Minimal satu jenis aktivitas pembelajaran harus diaktifkan.';
    }
    const promptLen = countCharacters(form.additional_prompt);
    if (promptLen > MAX_PROMPT_LENGTH) {
      validationErrors.additional_prompt = `Prompt tambahan tidak boleh melebihi ${MAX_PROMPT_LENGTH} karakter.`;
    }

    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setErrors({});

    const payload = {
      teaching_style: form.teaching_style,
      expertise: form.expertise,
      delivery_preference: form.delivery_preference,
      additional_prompt: form.additional_prompt,
      activity_configuration: { ...form.activity_configuration },
      ...(form.language_preference ? { language_preference: form.language_preference } : {}),
    };

    if (onSubmit) {
      try {
        setIsSubmitting(true);
        const result = await onSubmit(payload);
        setSaved(true);
        onSaved?.(result ?? payload);
      } catch (err) {
        setSubmitError(err);
      } finally {
        setIsSubmitting(false);
      }
    } else {
      const result = await saveAction.run(payload).catch(() => null);
      if (result) {
        setSaved(true);
        onSaved?.(result);
      }
    }
  };

  if (loading) {
    return (
      <div className="py-6">
        <Spinner label="Memuat profil pengajar…" />
      </div>
    );
  }

  const promptCharCount = countCharacters(form.additional_prompt);
  const isPromptOverLimit = promptCharCount > MAX_PROMPT_LENGTH;

  return (
    <form onSubmit={handleSubmit} className="form" noValidate>
      <ErrorAlert error={currentError} onClose={clearCurrentError} />

      {/* Section 1: Instructor Profile */}
      <div className="flex flex-col gap-4 border-b border-line pb-4">
        <h3 className="text-base font-bold text-ink">1. Profil Pengajar</h3>

        <Field
          label="Gaya mengajar"
          hint="Contoh: Interaktif, berbasis proyek, banyak studi kasus kontekstual."
        >
          <textarea
            id="instructor_teaching_style"
            name="teaching_style"
            rows={3}
            value={form.teaching_style}
            onChange={update('teaching_style')}
            placeholder="Deskripsikan gaya mengajar yang diinginkan..."
            disabled={isSaving}
          />
        </Field>

        <Field
          label="Bidang keahlian"
          hint="Contoh: Rekayasa Perangkat Lunak, Kecerdasan Buatan, Sistem Terdistribusi."
        >
          <input
            id="instructor_expertise"
            type="text"
            name="expertise"
            value={form.expertise}
            onChange={update('expertise')}
            placeholder="Masukkan bidang keahlian Anda..."
            disabled={isSaving}
          />
        </Field>

        <Field
          label="Preferensi penyampaian"
          hint="Contoh: Penjelasan konsep mendalam secara bertahap, perbanyak contoh kode praktis."
        >
          <textarea
            id="instructor_delivery_preference"
            name="delivery_preference"
            rows={2}
            value={form.delivery_preference}
            onChange={update('delivery_preference')}
            placeholder="Deskripsikan preferensi penyampaian materi..."
            disabled={isSaving}
          />
        </Field>
      </div>

      {/* Section 2: Additional Prompt */}
      <div className="flex flex-col gap-4 border-b border-line pb-4">
        <h3 className="text-base font-bold text-ink">2. Prompt Tambahan (AI Agent)</h3>

        <Field
          label="Prompt tambahan"
          hint="Instruksi tambahan opsional untuk memandu AI agent dalam merancang rencana pembelajaran dan materi mingguan."
          error={errors.additional_prompt}
          errorId="additional_prompt_error"
        >
          <textarea
            id="instructor_additional_prompt"
            name="additional_prompt"
            rows={4}
            value={form.additional_prompt}
            onChange={update('additional_prompt')}
            placeholder="Masukkan instruksi khusus atau konteks tambahan untuk agent..."
            aria-describedby={errors.additional_prompt ? 'additional_prompt_error' : undefined}
            aria-invalid={errors.additional_prompt ? 'true' : undefined}
            className={errors.additional_prompt ? 'border-danger focus:border-danger focus:ring-danger/20' : undefined}
            disabled={isSaving}
          />
          <div className="mt-1 flex justify-end text-xs text-muted">
            <span
              data-testid="prompt-char-counter"
              className={isPromptOverLimit ? 'font-semibold text-danger' : ''}
            >
              {promptCharCount} / {MAX_PROMPT_LENGTH} karakter
            </span>
          </div>
        </Field>
      </div>

      {/* Section 3: Activity Configuration */}
      <div className="flex flex-col gap-3 border-b border-line pb-4">
        <h3 className="text-base font-bold text-ink">3. Konfigurasi Aktivitas Pembelajaran</h3>
        <p className="text-xs text-muted">
          Pilih jenis aktivitas pembelajaran yang boleh dihasilkan oleh AI agent:
        </p>

        <fieldset
          className="checks"
          aria-describedby={errors.activity_configuration ? 'activity_configuration_error' : undefined}
          aria-invalid={errors.activity_configuration ? 'true' : undefined}
        >
          <legend className="sr-only">Jenis aktivitas yang diaktifkan</legend>
          {ACTIVITY_OPTIONS.map((opt) => (
            <label key={opt.key} className="check">
              <input
                type="checkbox"
                name={opt.key}
                checked={!!form.activity_configuration[opt.key]}
                onChange={handleActivityToggle(opt.key)}
                disabled={isSaving}
              />
              <span>
                <strong className="font-medium text-ink">{opt.label}</strong>
                <small className="muted"> — {opt.hint}</small>
              </span>
            </label>
          ))}
        </fieldset>

        {errors.activity_configuration && (
          <span
            id="activity_configuration_error"
            className="text-xs font-semibold text-danger"
            role="alert"
          >
            {errors.activity_configuration}
          </span>
        )}
      </div>

      {/* Form Action Buttons & Feedback */}
      <div className="flex flex-col gap-2 pt-2">
        {saved && (
          <Alert tone="success" onClose={() => setSaved(false)}>
            Profil tersimpan.
          </Alert>
        )}
        <div className="form__actions">
          <button
            type="button"
            className="btn btn--ghost"
            onClick={handleReset}
            disabled={isSaving}
          >
            Batal
          </button>
          <button
            type="submit"
            className="btn btn--primary"
            disabled={isSaving}
          >
            {isSaving ? (
              <span className="flex items-center gap-2">
                <span className="size-4 animate-spin rounded-full border-2 border-white/30 border-t-white motion-reduce:animate-none" aria-hidden="true" />
                <span>Menyimpan…</span>
              </span>
            ) : (
              'Simpan profil'
            )}
          </button>
        </div>
      </div>
    </form>
  );
}

export { InstructorSetupForm };
