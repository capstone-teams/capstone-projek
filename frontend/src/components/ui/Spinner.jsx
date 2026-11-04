export function Spinner({ label = 'Memuat…' }) {
  return (
    <div className="flex items-center gap-2.5 py-2 text-muted" role="status">
      <span className="size-4 animate-spin rounded-full border-2 border-line border-t-primary motion-reduce:animate-none" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
