import { useEffect } from 'react';
const SingleToast = ({ toast, onDismiss }) => {
    useEffect(() => {
        const timer = setTimeout(() => {
            onDismiss(toast.id);
        }, 3500);
        return () => clearTimeout(timer);
    }, [toast.id, onDismiss]);
    const accent = toast.type === 'success' ? 'border-l-[#10B981]' : 'border-l-[#2563EB]';
    return (<div className={`pointer-events-auto flex min-w-[280px] max-w-[420px] animate-toast-in items-center justify-between gap-3 rounded-lg border-l-4 bg-ink px-4 py-3 text-[13px] leading-[1.4] text-white shadow-[0_10px_15px_-3px_rgba(0,0,0,0.15),0_4px_6px_-2px_rgba(0,0,0,0.1)] max-sm:w-full max-sm:min-w-0 max-sm:max-w-full ${accent}`}>
      <span className="flex-1">{toast.message}</span>
      <button type="button" className="cursor-pointer rounded border-none bg-transparent px-1 py-0.5 text-[14px] text-[#94A3B8] transition-colors duration-150 ease-[ease] hover:text-white" onClick={() => onDismiss(toast.id)} aria-label="Tutup notifikasi">
        ✕
      </button>
    </div>);
};
export const Toast = ({ toasts, onDismiss }) => {
    if (toasts.length === 0)
        return null;
    return (<div className="pointer-events-none fixed right-6 bottom-6 z-100 flex flex-col gap-2.5 max-sm:right-4 max-sm:bottom-4 max-sm:left-4 max-sm:items-stretch" role="region" aria-live="polite">
      {toasts.map((t) => (<SingleToast key={t.id} toast={t} onDismiss={onDismiss}/>))}
    </div>);
};
