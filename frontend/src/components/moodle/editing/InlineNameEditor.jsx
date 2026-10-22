import { useRef, useState } from 'react';

/**
 * Nama yang dapat diubah langsung (ikon pensil, seperti inplace editable Moodle).
 * Enter atau keluar dari kolom menyimpan, Escape membatalkan. onSave mengembalikan true bila berhasil.
 */
export default function InlineNameEditor({ name, itemLabel, onSave, disabled = false, children }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(name);
  const saving = useRef(false);
  // Escape menutup kolom; blur yang menyusul tidak boleh ikut menyimpan.
  const cancelled = useRef(false);
  const pencilRef = useRef(null);

  const start = () => {
    cancelled.current = false;
    setValue(name);
    setEditing(true);
  };
  const stop = () => {
    setEditing(false);
    // Kembalikan fokus ke tombol pensil setelah kolom ditutup.
    setTimeout(() => pencilRef.current?.focus());
  };
  const save = async () => {
    if (saving.current || cancelled.current) return;
    const next = value.trim();
    if (!next || next === name) return stop();
    saving.current = true;
    const ok = await onSave(next);
    saving.current = false;
    if (ok) stop();
  };

  if (editing) {
    return (
      <form
        className="flex min-w-0 flex-1 items-center gap-2"
        onSubmit={(event) => { event.preventDefault(); save(); }}
      >
        <input
          className="min-w-0 flex-1 py-1 text-base font-semibold"
          aria-label={`Nama baru untuk ${itemLabel}`}
          value={value}
          maxLength={255}
          autoFocus
          onChange={(event) => setValue(event.target.value)}
          onBlur={save}
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              event.preventDefault();
              cancelled.current = true;
              stop();
            }
          }}
        />
        <span className="hidden text-xs text-muted sm:inline">Enter simpan · Esc batal</span>
      </form>
    );
  }

  return (
    <span className="inline-flex min-w-0 items-center gap-1.5">
      {children}
      <button
        ref={pencilRef}
        type="button"
        className="grid size-7 shrink-0 cursor-pointer place-items-center rounded-full text-sm text-muted transition-colors hover:bg-line-subtle hover:text-ink focus-visible:outline-2 focus-visible:outline-primary disabled:opacity-50"
        aria-label={`Ubah nama ${itemLabel}`}
        title="Ubah nama"
        disabled={disabled}
        onClick={start}
      >
        <span aria-hidden="true">✎</span>
      </button>
    </span>
  );
}
