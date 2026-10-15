import { useState } from 'react';
import { AUTH_INPUT_CLASS } from './authStyles';
import AuthFieldGroup from './AuthFieldGroup';

/** Input kata sandi dengan tombol tampilkan/sembunyikan. */
export default function PasswordField({ id, label, ...inputProps }) {
  const [visible, setVisible] = useState(false);
  return (
    <AuthFieldGroup id={id} label={label}>
      <div className="relative">
        <input id={id} className={`${AUTH_INPUT_CLASS} pr-[100px]`} type={visible ? 'text' : 'password'} {...inputProps} />
        <button
          type="button"
          className="absolute top-1/2 right-2 z-1 flex h-8 -translate-y-1/2 cursor-pointer items-center justify-center gap-1 rounded-[6px] px-2 text-[12px] whitespace-nowrap text-[#6b7280] focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[rgba(37,99,235,0.3)]"
          onClick={() => setVisible((value) => !value)}
          aria-label={visible ? 'Sembunyikan kata sandi' : 'Tampilkan kata sandi'}
          aria-pressed={visible}
        >
          {visible ? (
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"></path>
              <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"></path>
              <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"></path>
              <line x1="1" y1="1" x2="23" y2="23"></line>
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
              <circle cx="12" cy="12" r="3"></circle>
            </svg>
          )}
        </button>
      </div>
    </AuthFieldGroup>
  );
}
