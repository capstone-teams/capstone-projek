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
