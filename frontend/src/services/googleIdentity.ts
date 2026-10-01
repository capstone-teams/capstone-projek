/**
 * Pemuat Google Identity Services (tombol "Sign in with Google").
 * https://developers.google.com/identity/gsi/web/reference/js-reference
 */

export const GOOGLE_CLIENT_ID: string | null = import.meta.env.VITE_GOOGLE_CLIENT_ID?.trim() || null

const GSI_SCRIPT_SRC = 'https://accounts.google.com/gsi/client'

export interface GoogleCredentialResponse {
  credential: string
}

export interface GoogleAccountsId {
  initialize(config: {
    client_id: string
    callback: (response: GoogleCredentialResponse) => void
    auto_select?: boolean
    ux_mode?: 'popup' | 'redirect'
    context?: 'signin' | 'signup' | 'use'
  }): void
  renderButton(
    parent: HTMLElement,
    options: {
      type?: 'standard' | 'icon'
      theme?: 'outline' | 'filled_blue' | 'filled_black'
      size?: 'large' | 'medium' | 'small'
      text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin'
      shape?: 'rectangular' | 'pill' | 'circle' | 'square'
      logo_alignment?: 'left' | 'center'
      width?: number
      locale?: string
    },
  ): void
  disableAutoSelect(): void
}

interface GoogleNamespace {
  accounts: { id: GoogleAccountsId }
}

declare global {
  interface Window {
    google?: GoogleNamespace
  }
}

let loader: Promise<GoogleAccountsId> | null = null

export function loadGoogleIdentity(): Promise<GoogleAccountsId> {
  if (window.google?.accounts?.id) return Promise.resolve(window.google.accounts.id)
  if (loader) return loader

  loader = new Promise<GoogleAccountsId>((resolve, reject) => {
    const script = document.createElement('script')
    script.src = GSI_SCRIPT_SRC
    script.async = true
    script.defer = true
    script.onload = () => {
      const id = window.google?.accounts?.id
      if (id) resolve(id)
      else reject(new Error('Google Identity Services tidak tersedia.'))
    }
    script.onerror = () => reject(new Error('Gagal memuat Google Identity Services.'))
    document.head.appendChild(script)
  }).catch((err: unknown) => {
    loader = null // izinkan mencoba lagi pada render berikutnya
    throw err
  })

  return loader
}
