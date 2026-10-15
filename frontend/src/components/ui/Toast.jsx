import { useEffect } from 'react';
import styles from './Toast.module.css';
const SingleToast = ({ toast, onDismiss }) => {
    useEffect(() => {
        const timer = setTimeout(() => {
            onDismiss(toast.id);
        }, 3500);
        return () => clearTimeout(timer);
    }, [toast.id, onDismiss]);
    return (<div className={`${styles.toast} ${toast.type === 'success' ? styles.toastSuccess : styles.toastInfo}`}>
      <span className={styles.toastMessage}>{toast.message}</span>
      <button type="button" className={styles.toastCloseBtn} onClick={() => onDismiss(toast.id)} aria-label="Tutup notifikasi">
        ✕
      </button>
    </div>);
};
export const Toast = ({ toasts, onDismiss }) => {
    if (toasts.length === 0)
        return null;
    return (<div className={styles.toastContainer} role="region" aria-live="polite">
      {toasts.map((t) => (<SingleToast key={t.id} toast={t} onDismiss={onDismiss}/>))}
    </div>);
};
