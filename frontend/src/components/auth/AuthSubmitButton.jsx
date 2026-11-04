/** Tombol submit utama di form auth. */
export default function AuthSubmitButton({ children, disabled }) {
  return (
    <div className="mt-2 flex flex-wrap gap-3 max-phone:flex-col">
      <button
        type="submit"
        className="inline-flex h-11 min-w-[160px] flex-1 cursor-pointer items-center justify-center rounded-lg border border-primary bg-primary text-[13px] font-semibold text-white transition-all duration-150 ease-[ease] hover:border-primary-dark hover:bg-primary-dark max-phone:min-h-11 max-phone:w-full"
        disabled={disabled}
      >
        {children}
      </button>
    </div>
  );
}
