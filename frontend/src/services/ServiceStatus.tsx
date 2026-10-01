import type { ApiError } from './apiError.ts'

interface ServiceStatusProps {
  error?: ApiError
  onRetry?: () => void
}

export function ServiceStatus({ error, onRetry }: ServiceStatusProps) {
  if (!error) return <p role="status">Memuat data...</p>

  return (
    <div role="alert">
      <p>{error.message}</p>
      {onRetry && <button type="button" onClick={onRetry}>Coba lagi</button>}
    </div>
  )
}
