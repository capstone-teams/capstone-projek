export function EmptyState({ title, children, action }) {
  return (
    <div className="px-3 py-8 text-center">
      <p className="mb-1 font-semibold">{title}</p>
      {children && <p className="text-muted">{children}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}
