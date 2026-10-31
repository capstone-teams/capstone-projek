import { createContext, useContext, useId, useState } from 'react';

/*
 * Potongan formulir Moodle (lib/form, tema Boost): bagian yang dapat dilipat dengan "Expand all",
 * baris label di kiri dan isian di kanan, ikon wajib, serta date_time_selector dengan "Enable".
 */

const SectionsContext = createContext(null);
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const pad = (n) => String(n).padStart(2, '0');

/** Pembungkus bagian `ids`; `initiallyOpen` berisi bagian yang terbuka saat halaman dibuka (seperti setExpanded). */
export function FormSections({ ids, initiallyOpen, children }) {
  const [open, setOpen] = useState(() => new Set(initiallyOpen));
  const allOpen = ids.every((key) => open.has(key));
  return (
    <SectionsContext.Provider value={{ open, toggle: (key) => setOpen((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    }) }}
    >
      <div className="mb-2 flex justify-end">
        <button type="button" className="cursor-pointer text-sm text-primary hover:underline" onClick={() => setOpen(allOpen ? new Set() : new Set(ids))}>
          {allOpen ? 'Collapse all' : 'Expand all'}
        </button>
      </div>
      {children}
    </SectionsContext.Provider>
  );
}

export function FormSection({ id, title, children }) {
  const sections = useContext(SectionsContext);
  const open = sections.open.has(id);
  return (
    <fieldset className="border-b border-line py-3" aria-labelledby={`${id}-legend`}>
      <legend className="contents">
        <button
          id={`${id}-legend`}
          type="button"
          aria-expanded={open}
          aria-controls={`${id}-body`}
          className="flex cursor-pointer items-center gap-2 py-1 text-xl font-bold text-primary"
          onClick={() => sections.toggle(id)}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" aria-hidden="true" className={open ? '' : '-rotate-90'}>
            <path d="m6 9 6 6 6-6" />
          </svg>
          {title}
        </button>
      </legend>
      {/* Isi tetap terpasang saat dilipat agar nilai dan validasi tidak hilang, seperti di Moodle. */}
      <div id={`${id}-body`} hidden={!open} className="flex flex-col gap-4 pt-4 pb-2">{children}</div>
    </fieldset>
  );
}

export function RequiredIcon() {
  return (
    <span className="ml-1 inline-grid size-4 place-items-center rounded-full bg-danger align-middle text-[10px] font-bold text-white" title="Required field">
      !<span className="sr-only">Required field</span>
    </span>
  );
}

/** Satu baris formulir: label (col-md-3) dan isian (col-md-9), dengan pesan error Moodle di bawah isian. */
export function FormRow({ label, labelFor, labelId, required, error, errorId, children }) {
  return (
    <div className="grid gap-x-6 gap-y-1 md:grid-cols-[minmax(0,1fr)_minmax(0,3fr)]">
      <div className="md:pt-2">
        {labelFor ? <label htmlFor={labelFor} id={labelId}>{label}</label> : <span id={labelId}>{label}</span>}
        {required && <RequiredIcon />}
      </div>
      <div className="min-w-0">
        {children}
        {error && <p id={errorId} className="mt-1 text-sm text-danger">{error}</p>}
      </div>
    </div>
  );
}

const SELECT = 'w-auto! min-w-0 py-1.5! pr-8! pl-2!';

/**
 * date_time_selector: tanggal, bulan, tahun, jam, menit (+ Enable bila optional).
 * value = { enabled, date: Date }; onChange menerima value baru.
 */
export function DateTimeSelector({ label, value, onChange, optional = true, error, disabled }) {
  const id = useId();
  const { enabled, date } = value;
  const set = (patch) => {
    const next = new Date(date);
    if ('day' in patch) next.setDate(patch.day);
    if ('month' in patch) { const day = next.getDate(); next.setDate(1); next.setMonth(patch.month); next.setDate(Math.min(day, new Date(next.getFullYear(), patch.month + 1, 0).getDate())); }
    if ('year' in patch) next.setFullYear(patch.year);
    if ('hour' in patch) next.setHours(patch.hour);
    if ('minute' in patch) next.setMinutes(patch.minute);
    onChange({ enabled, date: next });
  };
  const off = disabled || (optional && !enabled);
  const year = date.getFullYear();
  return (
    <FormRow label={label} labelId={`${id}-label`} error={error} errorId={`${id}-error`}>
      <div role="group" aria-labelledby={`${id}-label`} aria-describedby={error ? `${id}-error` : undefined} data-invalid={error ? 'true' : undefined} className="flex flex-wrap items-center gap-2">
        <select aria-label="Day" className={SELECT} value={date.getDate()} disabled={off} onChange={(e) => set({ day: Number(e.target.value) })}>
          {Array.from({ length: 31 }, (_, i) => i + 1).map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
        <select aria-label="Month" className={SELECT} value={date.getMonth()} disabled={off} onChange={(e) => set({ month: Number(e.target.value) })}>
          {MONTHS.map((m, i) => <option key={m} value={i}>{m}</option>)}
        </select>
        <select aria-label="Year" className={SELECT} value={year} disabled={off} onChange={(e) => set({ year: Number(e.target.value) })}>
          {Array.from({ length: 11 }, (_, i) => year - 5 + i).map((y) => <option key={y} value={y}>{y}</option>)}
        </select>
        <select aria-label="Hour" className={SELECT} value={date.getHours()} disabled={off} onChange={(e) => set({ hour: Number(e.target.value) })}>
          {Array.from({ length: 24 }, (_, i) => i).map((h) => <option key={h} value={h}>{pad(h)}</option>)}
        </select>
        <select aria-label="Minute" className={SELECT} value={date.getMinutes()} disabled={off} onChange={(e) => set({ minute: Number(e.target.value) })}>
          {Array.from({ length: 60 }, (_, i) => i).map((m) => <option key={m} value={m}>{pad(m)}</option>)}
        </select>
        {optional && (
          <label className="flex items-center gap-1.5">
            <input type="checkbox" checked={enabled} disabled={disabled} onChange={(e) => onChange({ enabled: e.target.checked, date })} />
            Enable
          </label>
        )}
      </div>
    </FormRow>
  );
}
