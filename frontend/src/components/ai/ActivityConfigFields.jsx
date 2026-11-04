const OPTIONS = [
  { key: 'learning_material', label: 'Materi pembelajaran', hint: 'Halaman materi per minggu' },
  { key: 'assignment', label: 'Assignment', hint: 'Tugas di minggu tertentu' },
  { key: 'quiz', label: 'Quiz', hint: 'Kuis berkala dan ujian' },
];

const DEFAULT_CONFIG = {
  learning_material: true,
  assignment: true,
  quiz: true,
};

/** Checkbox konfigurasi aktivitas pembelajaran. */
export default function ActivityConfigFields({ value, onChange, disabled = false }) {
  const safeValue = value || DEFAULT_CONFIG;
  const activeCount = OPTIONS.filter((o) => safeValue[o.key]).length;

  return (
    <fieldset className="checks" disabled={disabled}>
      <legend className="field__label">Aktivitas yang dibuat</legend>
      {OPTIONS.map((o) => (
        <label key={o.key} className="check">
          <input
            type="checkbox"
            checked={!!safeValue[o.key]}
            // Minimal satu aktivitas harus tetap aktif.
            disabled={disabled || (safeValue[o.key] && activeCount === 1)}
            onChange={(e) => onChange?.({ ...safeValue, [o.key]: e.target.checked })}
          />
          <span>
            {o.label}
            <small className="muted"> — {o.hint}</small>
          </span>
        </label>
      ))}
    </fieldset>
  );
}
