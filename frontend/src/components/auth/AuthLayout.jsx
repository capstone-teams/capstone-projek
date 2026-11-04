import ApplicationHeader from '../layout/ApplicationHeader';

/** Kerangka halaman login/lupa password: header, panel brand (kiri), dan panel form (kanan). */
export default function AuthLayout({ heroTitle, title, children }) {
  return (
    <div className="approved-app">
      <ApplicationHeader />
      <main className="approved-login">
        <div className="flex flex-1 items-center justify-center px-6 py-[60px] max-phone:px-3 max-phone:py-5">
          <div className="flex w-full max-w-[960px] overflow-hidden rounded-lg border border-line bg-white shadow-[0_4px_6px_-1px_rgba(0,0,0,0.05)] max-tablet:flex-col">
            <div className="flex w-[440px] flex-col justify-between gap-8 bg-primary px-10 py-14 text-white max-tablet:w-full max-tablet:px-6 max-tablet:py-8 max-phone:gap-4 max-phone:px-4 max-phone:py-6">
              <div>
                <div className="mb-5 text-[12px] font-bold tracking-[0.1em] opacity-90">AGENTIC LMS</div>
                <h1 className="text-[32px] leading-[1.3] font-bold text-white max-phone:text-[22px]">{heroTitle}</h1>
              </div>
              <div className="text-[14px] font-medium opacity-85">Institut Teknologi Kalimantan</div>
            </div>
            <div className="flex flex-1 flex-col justify-center px-12 py-14 max-tablet:px-6 max-tablet:py-8 max-phone:px-4 max-phone:py-6">
              <h2 className="mb-6 text-[24px] font-bold text-ink max-phone:mb-[18px] max-phone:text-[20px]">{title}</h2>
              {children}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
