/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** OAuth Client ID (Web) dari Google Cloud Console. Kosong = pakai akun Google mock. */
  readonly VITE_GOOGLE_CLIENT_ID?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
