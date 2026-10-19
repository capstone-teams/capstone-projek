import styles from './Button.module.css';
export function Button({ children, variant = 'primary', size = 'md', iconLeft, iconRight, className = '', disabled, ...props }) {
    return (<button className={`${styles.button} ${styles[variant]} ${styles[size]} ${className}`.trim()} disabled={disabled} {...props}>
      {iconLeft}
      {children}
      {iconRight}
    </button>);
}
