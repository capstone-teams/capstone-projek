const OPTIONS = [
  { key: 'learning_material', label: 'Materi pembelajaran', hint: 'Halaman materi per minggu' },
  { key: 'assignment', label: 'Assignment', hint: 'Tugas di minggu tertentu' },
  { key: 'quiz', label: 'Quiz', hint: 'Kuis berkala dan ujian' },
];

/** Checkbox konfigurasi aktivitas (design-api.md §8.3). */
export default function ActivityConfigFields({ value, onChange, disabled = false }) {
  const activeCount = OPTIONS.filter((o) => value[o.key]).length;

  return (
    <fieldset className="checks" disabled={disabled}>
      <legend className="field__label">Aktivitas yang dibuat</legend>
      {OPTIONS.map((o) => (
        <label key={o.key} className="check">
          <input
            type="checkbox"
            checked={!!value[o.key]}
            // Minimal satu aktivitas harus tetap aktif.
            disabled={disabled || (value[o.key] && activeCount === 1)}
            onChange={(e) => onChange({ ...value, [o.key]: e.target.checked })}
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
