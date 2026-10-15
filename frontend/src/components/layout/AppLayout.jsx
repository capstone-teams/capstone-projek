import { AppNavbar } from './AppNavbar';
import { Toast } from '../ui/Toast';
import styles from './AppLayout.module.css';
export const AppLayout = ({ currentPath, activeRole, dosenProfile, onNavigate, onOpenModal, toasts, onDismissToast, children, }) => {
    return (<div className={styles.pageContainer}>
      <AppNavbar currentPath={currentPath} activeRole={activeRole} dosenProfile={dosenProfile} onNavigate={onNavigate}  onOpenModal={onOpenModal}/>
      <div className={styles.mainContent}>{children}</div>
      <Toast toasts={toasts} onDismiss={onDismissToast}/>
    </div>);
};
