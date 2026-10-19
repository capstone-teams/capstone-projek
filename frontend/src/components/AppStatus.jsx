import { useAppState } from '../hooks/useAppState';
import { Alert } from './ui';
import { Toast } from './ui/Toast';

/** Menampilkan loading global, error global dan notifikasi dari AppStateProvider. */
export default function AppStatus() {
  const { loading, errors, notifications, dismissError, dismissNotification } = useAppState();
  const current = loading.at(-1);

  return (
    <>
      {current && (
        <div className="app-global-loading" role="progressbar" aria-busy="true" aria-label={current.label}>
          <span className="app-global-loading__bar" aria-hidden="true" />
        </div>
      )}
      {errors.length > 0 && (
        <div className="approved-page app-global-errors">
          {errors.map((e) => (
            <Alert key={e.id} tone="danger" title={e.title} onClose={() => dismissError(e.id)}>
              {e.message}
            </Alert>
          ))}
        </div>
      )}
      <Toast toasts={notifications} onDismiss={dismissNotification} />
    </>
  );
}
