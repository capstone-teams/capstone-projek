/** Satu kontrol form auth. Label hanya untuk pembaca layar; petunjuk tampil sebagai placeholder. */
export default function AuthFieldGroup({ id, label, children }) {
  return (
    <div className="mb-4 flex flex-col">
      <label className="sr-only" htmlFor={id}>
        {label}
      </label>
      {children}
    </div>
  );
}
