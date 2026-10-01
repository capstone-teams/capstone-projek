import type { AppPath } from '../../types/navigation'
import type { UserRole } from '../../types/auth'
import { ROLE_LABELS } from '../../types/auth'
import { Button } from '../../components/ui/Button'
import { StatusPage } from './StatusPage'

interface UnauthorizedPageProps {
  role: UserRole | null
  homePath: AppPath
  onNavigate: (path: AppPath) => void
  onLogout: () => void
}

export function UnauthorizedPage({ role, homePath, onNavigate, onLogout }: UnauthorizedPageProps) {
  const description = role
    ? `Akun ${ROLE_LABELS[role]} Anda tidak memiliki akses ke halaman ini. Kembali ke beranda atau masuk dengan akun lain.`
    : 'Anda tidak memiliki akses ke halaman ini. Silakan masuk dengan akun yang sesuai.'

  return (
    <StatusPage
      code="403"
      title="Akses ditolak"
      description={description}
      actions={
        <>
          <Button onClick={() => onNavigate(homePath)}>Kembali ke Beranda</Button>
          {role && (
            <Button variant="secondary" onClick={onLogout}>
              Masuk dengan akun lain
            </Button>
          )}
        </>
      }
    />
  )
}
