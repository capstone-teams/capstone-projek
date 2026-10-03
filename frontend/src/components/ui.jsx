import { useEffect, useId, useRef } from 'react';
import { STATUS_LABELS, statusTone } from '../utils/workflow';
import { percent } from '../utils/format';

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl md:text-[1.75rem]">{title}</h1>
        {subtitle && <p className="mt-1 text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

/** Kotak bergaya "block"/card Moodle. */
export function Card({ title, actions, children, className = '' }) {
  return (
    <section className={`min-w-0 rounded-lg border border-line-subtle bg-white p-4 md:p-5 ${className}`}>
      {(title || actions) && (
        <header className="mb-3.5 flex flex-wrap items-center justify-between gap-3">
          {title && <h2 className="text-lg">{title}</h2>}
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

const BADGE_TONES = {
  neutral: 'bg-surface text-ink border border-line',
  success: 'bg-success-light text-success',
  warning: 'bg-warning-light text-warning',
  danger: 'bg-danger-light text-danger',
  info: 'bg-primary-light text-primary',
  primary: 'bg-primary text-white',
};

export function Badge({ tone = 'neutral', children }) {
  return (
    <span className={`inline-flex items-center whitespace-nowrap rounded px-2 py-0.5 text-xs font-bold ${BADGE_TONES[tone] ?? BADGE_TONES.neutral}`}>
      {children}
    </span>
  );
}

export function StatusBadge({ status }) {
  return <Badge tone={statusTone(status)}>{STATUS_LABELS[status] ?? status}</Badge>;
}

export function Spinner({ label = 'Memuat…' }) {
  return (
    <div className="flex items-center gap-2.5 py-2 text-muted" role="status">
      <span className="size-4 animate-spin rounded-full border-2 border-line border-t-primary motion-reduce:animate-none" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

const ALERT_TONES = {
  danger: 'bg-danger-light text-[#6c1a11] border-[#efc1bc]',
  success: 'bg-success-light text-[#1c411b] border-[#c3d9c2]',
  warning: 'bg-warning-light text-[#5c3700] border-[#f8dfb8]',
  info: 'bg-primary-light text-[#083863] border-[#b7d3ec]',
};

export function Alert({ tone = 'danger', title, children, onClose }) {
  if (!children && !title) return null;
  return (
    <div
      className={`mb-3 flex justify-between gap-3 rounded-md border px-4 py-3 ${ALERT_TONES[tone]}`}
      role={tone === 'danger' ? 'alert' : 'status'}
    >
      <div className="min-w-0">
        {title && <strong className="block">{title}</strong>}
        {children && <div>{children}</div>}
      </div>
      {onClose && (
        <button type="button" className="cursor-pointer text-xl leading-none opacity-60 hover:opacity-100" onClick={onClose} aria-label="Tutup">
          ×
        </button>
      )}
    </div>
  );
}

export function ErrorAlert({ error, onClose }) {
  if (!error) return null;
  const code = error.code && !['INTERNAL_ERROR', 'networkerror'].includes(error.code) ? error.code : undefined;
  return (
    <Alert tone="danger" onClose={onClose} title={code}>
      {error.message}
    </Alert>
  );
}

export function EmptyState({ title, children, action }) {
  return (
    <div className="px-3 py-8 text-center">
      <p className="mb-1 font-semibold">{title}</p>
      {children && <p className="text-muted">{children}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

export function ProgressBar({ completed = 0, total = 0, label }) {
  const value = percent(completed, total);
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex justify-between gap-2 text-sm text-muted">
        <span>{label}</span>
        <span>
          {completed}/{total} ({value}%)
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-line" role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-full rounded-full bg-primary transition-[width] duration-300" style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

export function Modal({ open, title, onClose, children, footer }) {
  const ref = useRef(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal?.();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className="m-auto w-[min(520px,calc(100vw-32px))] rounded-lg border border-line bg-white p-0 text-ink shadow-xl"
      aria-labelledby={titleId}
      onCancel={onClose}
      onClose={onClose}
    >
      <header className="flex items-center justify-between gap-2 border-b border-line px-5 py-3.5">
        <h2 id={titleId} className="text-lg">
          {title}
        </h2>
        <button type="button" className="cursor-pointer text-2xl leading-none text-muted hover:text-ink" onClick={onClose} aria-label="Tutup">
          ×
        </button>
      </header>
      <div className="p-5">{children}</div>
      {footer && <footer className="flex justify-end gap-2 border-t border-line px-5 py-3.5">{footer}</footer>}
    </dialog>
  );
}

export function Field({ label, hint, children }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-sm font-semibold">{label}</span>
      {children}
      {hint && <span className="text-xs text-muted">{hint}</span>}
    </label>
  );
}

/** Avatar user: foto dari Moodle bila ada, selain itu inisial. */
export function Avatar({ name = '', src, size = 'md' }) {
  const sizes = { sm: 'size-7 text-xs', md: 'size-9 text-sm', lg: 'size-20 text-2xl' };
  const initials = name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0])
    .join('')
    .toUpperCase();
  // URL default Moodle (u/f1, u/f2) adalah gambar siluet; tampilkan inisial saja.
  const usable = src && !/\/u\/f\d/.test(src);
  return usable ? (
    <img src={src} alt="" className={`${sizes[size]} shrink-0 rounded-full object-cover`} />
  ) : (
    <span className={`${sizes[size]} grid shrink-0 place-items-center rounded-full bg-[#e3e7eb] font-bold text-muted`} aria-hidden="true">
      {initials || '?'}
    </span>
  );
}
