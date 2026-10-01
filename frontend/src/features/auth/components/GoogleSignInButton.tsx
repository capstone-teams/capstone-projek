import { useEffect, useRef, useState } from 'react'
import { loadGoogleIdentity } from '../../../services/googleIdentity'
import styles from '../LoginPage.module.css'

interface GoogleSignInButtonProps {
  clientId: string
  onCredential: (idToken: string) => void
}

/**
 * Tombol resmi "Sign in with Google". Google membuka popup akun dan
 * mengembalikan ID token lewat `onCredential`.
 */
export function GoogleSignInButton({ clientId, onCredential }: GoogleSignInButtonProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const onCredentialRef = useRef(onCredential)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')

  useEffect(() => {
    onCredentialRef.current = onCredential
  }, [onCredential])

  useEffect(() => {
    let cancelled = false

    loadGoogleIdentity()
      .then((googleId) => {
        const container = containerRef.current
        if (cancelled || !container) return
        googleId.initialize({
          client_id: clientId,
          callback: (response) => onCredentialRef.current(response.credential),
          auto_select: false,
          ux_mode: 'popup',
          context: 'signin',
        })
        googleId.renderButton(container, {
          type: 'standard',
          theme: 'outline',
          size: 'large',
          text: 'signin_with',
          shape: 'rectangular',
          logo_alignment: 'center',
          width: Math.min(400, Math.max(200, container.offsetWidth)),
          locale: 'id',
        })
        setStatus('ready')
      })
      .catch(() => {
        if (!cancelled) setStatus('error')
      })

    return () => {
      cancelled = true
    }
  }, [clientId])

  return (
    <div>
      <div ref={containerRef} className={styles.googleButtonSlot} aria-busy={status === 'loading'} />
      {status === 'error' && (
        <p className={`${styles.fieldError} ${styles.socialError}`} role="alert">
          Gagal memuat login Google. Periksa koneksi internet lalu muat ulang halaman.
        </p>
      )}
    </div>
  )
}
