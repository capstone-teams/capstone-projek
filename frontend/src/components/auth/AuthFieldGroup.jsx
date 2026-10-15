/** Label di atas satu kontrol form auth. */
export default function AuthFieldGroup({ id, label, children }) {
  return (
    <div className="mb-4 flex flex-col gap-1.5">
      <label className="text-[13px] font-semibold text-[#334155]" htmlFor={id}>
        {label}
      </label>
      {children}
    </div>
  );
}
