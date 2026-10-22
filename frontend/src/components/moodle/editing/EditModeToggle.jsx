/** Saklar "Mode edit" di header kursus (hanya untuk pengguna yang boleh mengubah kursus). */
export default function EditModeToggle({ checked, onChange }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      className="inline-flex min-h-11 cursor-pointer items-center gap-2.5 rounded-full border border-line bg-white px-3.5 py-1.5 text-sm font-semibold text-ink transition-colors hover:bg-surface focus-visible:outline-2 focus-visible:outline-primary"
      onClick={() => onChange(!checked)}
    >
      Mode edit
      <span
        aria-hidden="true"
        className={`relative h-6 w-11 rounded-full transition-colors ${checked ? 'bg-primary' : 'bg-line'}`}
      >
        <span className={`absolute top-0.5 left-0.5 size-5 rounded-full bg-white shadow transition-transform ${checked ? 'translate-x-5' : ''}`} />
      </span>
    </button>
  );
}
