/** @param {{ error?: import('./apiError.js').ApiError, onRetry?: () => void }} props */
export function ServiceStatus({ error, onRetry }) {
  if (!error) return <p role="status">Memuat data...</p>

  return (
    <div role="alert">
      <p>{error.message}</p>
      {onRetry && <button type="button" onClick={onRetry}>Coba lagi</button>}
    </div>
  )
}
