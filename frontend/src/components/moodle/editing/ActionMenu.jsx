import { useEffect, useRef, useState } from 'react';

const ITEM_CLASS =
  'flex w-full cursor-pointer items-center justify-between gap-3 border-none bg-transparent px-4 py-2 text-left text-sm no-underline transition-colors focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50';
const TONE_CLASS = {
  default: 'text-ink hover:bg-line-subtle hover:text-ink focus-visible:bg-line-subtle',
  danger: 'text-danger hover:bg-danger-light hover:text-danger focus-visible:bg-danger-light',
};

/**
 * Tombol ⋮ dengan daftar aksi (pola menu ARIA: panah atas/bawah, Home/End, Escape).
 * items: [{ key, label, onSelect | href, danger, disabled }]. href dibuka di tab baru (halaman Moodle).
 */
export default function ActionMenu({ label, items, disabled = false }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const triggerRef = useRef(null);
  const menuRef = useRef(null);

  const menuItems = () => [...(menuRef.current?.querySelectorAll('[role="menuitem"]:not([disabled])') ?? [])];
  const close = (focusTrigger) => {
    setOpen(false);
    if (focusTrigger) triggerRef.current?.focus();
  };

  useEffect(() => {
    if (!open) return undefined;
    menuItems()[0]?.focus();
    const outside = (event) => !rootRef.current?.contains(event.target) && setOpen(false);
    document.addEventListener('mousedown', outside);
    return () => document.removeEventListener('mousedown', outside);
  }, [open]);

  const onKeyDown = (event) => {
    const list = menuItems();
    const index = list.indexOf(document.activeElement);
    const focus = (i) => { event.preventDefault(); list[(i + list.length) % list.length]?.focus(); };
    if (event.key === 'Escape') { event.preventDefault(); close(true); }
    else if (event.key === 'ArrowDown') focus(index + 1);
    else if (event.key === 'ArrowUp') focus(index - 1);
    else if (event.key === 'Home') focus(0);
    else if (event.key === 'End') focus(list.length - 1);
    else if (event.key === 'Tab') setOpen(false);
  };

  const select = (item) => {
    close(true);
    item.onSelect?.();
  };

  return (
    <div className="relative" ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className="grid size-9 cursor-pointer place-items-center rounded-full text-lg leading-none text-muted transition-colors hover:bg-line-subtle hover:text-ink focus-visible:outline-2 focus-visible:outline-primary disabled:cursor-not-allowed disabled:opacity-50"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => setOpen((value) => !value)}
      >
        <span aria-hidden="true">⋮</span>
      </button>
      {open && (
        <div
          ref={menuRef}
          role="menu"
          aria-label={label}
          className="absolute top-[calc(100%+4px)] right-0 z-40 w-60 rounded-lg border border-line bg-white py-1.5 shadow-[0_10px_15px_-3px_rgba(0,0,0,0.1),0_4px_6px_-2px_rgba(0,0,0,0.05)]"
          onKeyDown={onKeyDown}
        >
          {items.map((item) =>
            item.href ? (
              <a key={item.key} role="menuitem" href={item.href} target="_blank" rel="noreferrer" className={`${ITEM_CLASS} ${TONE_CLASS.default}`} onClick={() => close(false)}>
                {item.label}
                <span aria-hidden="true" className="text-xs text-muted">↗</span>
                <span className="sr-only">(dibuka di Moodle, tab baru)</span>
              </a>
            ) : (
              <button
                key={item.key}
                type="button"
                role="menuitem"
                className={`${ITEM_CLASS} ${TONE_CLASS[item.danger ? 'danger' : 'default']}`}
                disabled={item.disabled}
                onClick={() => select(item)}
              >
                {item.label}
              </button>
            ),
          )}
        </div>
      )}
    </div>
  );
}
