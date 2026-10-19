import styles from './Card.module.css';
export function Card({ children, padding = 'md', interactive = false, className = '', ...props }) {
    const paddingClass = padding === 'none'
        ? styles.paddingNone
        : padding === 'sm'
            ? styles.paddingSm
            : padding === 'lg'
                ? styles.paddingLg
                : styles.paddingMd;
    return (<div className={`${styles.card} ${paddingClass} ${interactive ? styles.interactive : ''} ${className}`.trim()} {...props}>
      {children}
    </div>);
}
