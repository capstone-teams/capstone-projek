import type { ReactNode } from 'react'
import styles from './StatusPage.module.css'

interface StatusPageProps {
  code: string
  title: string
  description: string
  actions: ReactNode
}

export function StatusPage({ code, title, description, actions }: StatusPageProps) {
  return (
    <div className={styles.container}>
      <section className={styles.card} aria-labelledby="status-title">
        <span className={styles.code}>{code}</span>
        <h1 id="status-title" className={styles.title}>
          {title}
        </h1>
        <p className={styles.description}>{description}</p>
        <div className={styles.actions}>{actions}</div>
      </section>
    </div>
  )
}
