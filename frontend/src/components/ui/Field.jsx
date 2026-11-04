export function Field({ label, hint, required, error, errorId, children }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-sm font-semibold">
        {label}
        {required && (
          <>
            <span className="text-danger" aria-hidden="true"> *</span>
            <span className="sr-only"> (wajib diisi)</span>
          </>
        )}
      </span>
      {children}
      {error && (
        <span id={errorId} className="text-xs font-semibold text-danger">
          {error}
        </span>
      )}
      {hint && <span className="text-xs text-muted">{hint}</span>}
    </label>
  );
}
