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
