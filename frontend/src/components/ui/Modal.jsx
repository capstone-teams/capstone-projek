import { useEffect, useId, useRef } from 'react';

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
