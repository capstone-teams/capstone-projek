import { Badge } from './Badge';
import styles from './PlaceholderView.module.css';
export function PlaceholderView({ icon, title, description, issueNumber, }) {
    return (<div className={styles.container}>
      <div className={styles.iconWrapper}>{icon}</div>
      <h2 className={styles.title}>{title}</h2>
      <p className={styles.description}>{description}</p>
      <div className={styles.badge}>
        <Badge variant="info">Dikerjakan pada {issueNumber}</Badge>
      </div>
    </div>);
}
