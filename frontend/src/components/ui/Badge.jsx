import styles from './Badge.module.css';
export function Badge({ children, variant = 'neutral', withDot = true, className = '', }) {
    return (<span className={`${styles.badge} ${styles[variant]} ${className}`.trim()}>
      {withDot && <span className={styles.dot} aria-hidden="true"/>}
      <span>{children}</span>
    </span>);
}
