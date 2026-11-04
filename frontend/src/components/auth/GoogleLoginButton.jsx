/** Pemisah "atau" diikuti tombol masuk dengan Google. */
export default function GoogleLoginButton({ onClick }) {
  return (
    <>
      <div className="my-[18px] flex items-center gap-3 text-[12px] text-muted before:h-px before:flex-1 before:bg-line before:content-[''] after:h-px after:flex-1 after:bg-line after:content-['']">
        <span>atau</span>
      </div>
      <button
        type="button"
        className="inline-flex min-h-11 w-full cursor-pointer items-center justify-center gap-2.5 rounded-lg border border-[#CBD5E1] bg-white font-[inherit] text-[13px] font-semibold text-[#334155] transition-colors duration-150 ease-[ease] hover:border-[#94A3B8] hover:bg-surface focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[rgba(37,99,235,0.3)]"
        onClick={onClick}
      >
        <svg className="size-5 flex-none" viewBox="0 0 24 24" aria-hidden="true">
          <path fill="#4285F4" d="M23.49 12.27c0-.78-.07-1.53-.2-2.27H12v4.51h6.44a5.5 5.5 0 0 1-2.39 3.61v3h3.87c2.27-2.09 3.57-5.17 3.57-8.85Z" />
          <path fill="#34A853" d="M12 24c3.24 0 5.96-1.08 7.95-2.92l-3.87-3c-1.08.72-2.46 1.15-4.08 1.15-3.14 0-5.8-2.12-6.75-4.97H1.25v3.09A12 12 0 0 0 12 24Z" />
          <path fill="#FBBC05" d="M5.25 14.26a7.2 7.2 0 0 1 0-4.52V6.65H1.25a12 12 0 0 0 0 10.7l4-3.09Z" />
          <path fill="#EA4335" d="M12 4.77c1.77 0 3.35.61 4.6 1.8l3.45-3.45C17.95 1.16 15.24 0 12 0A12 12 0 0 0 1.25 6.65l4 3.09C6.2 6.89 8.86 4.77 12 4.77Z" />
        </svg>
        Lanjutkan dengan Google
      </button>
    </>
  );
}
