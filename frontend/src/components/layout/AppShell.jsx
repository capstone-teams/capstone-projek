import { useState } from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import styles from './AppShell.module.css';
export function AppShell({ children, activeTab, onSelectTab, title, breadcrumb, }) {
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    return (<div className={styles.shell}>
      <Sidebar activeTab={activeTab} onSelectTab={onSelectTab} isOpen={isMobileMenuOpen} onClose={() => setIsMobileMenuOpen(false)}/>
      <div className={styles.contentWrapper}>
        <Header title={title} breadcrumb={breadcrumb} onToggleMobileMenu={() => setIsMobileMenuOpen((prev) => !prev)}/>
        <main className={styles.mainContainer}>{children}</main>
      </div>
    </div>);
}
