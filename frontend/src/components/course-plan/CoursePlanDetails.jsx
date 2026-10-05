import { Badge, EmptyState } from '../ui';
import styles from './CoursePlanDetails.module.css';

const ACTIVITY_LABELS = { learning_material: 'Materi', assignment: 'Tugas', quiz: 'Kuis' };

function TextList({ items }) {
  return items.length ? (
    <ul className={styles.textList}>
      {items.map((item, index) => <li key={index}>{item}</li>)}
    </ul>
  ) : <span className="muted">Belum tersedia.</span>;
}

function Activities({ items }) {
  return items.length ? (
    <div className={styles.activities}>
      {items.map((activity, index) => <Badge key={index}>{ACTIVITY_LABELS[activity] ?? activity}</Badge>)}
    </div>
  ) : <span className="muted">Belum tersedia.</span>;
}

/** Presentasi rencana saja; aksi approve/regenerasi tetap di CoursePlanPage. */
export default function CoursePlanDetails({ plan, course }) {
  const info = plan.course ?? {};
  const outcomes = Array.isArray(plan.learning_outcomes) ? plan.learning_outcomes : [];
  const descriptions = new Map(outcomes.filter((item) => item?.code).map((item) => [item.code, item.description]));
  const outcomeText = (code) => descriptions.get(code) ? `${code} — ${descriptions.get(code)}` : code;

  return (
    <div className={styles.details}>
      <dl className={styles.information} aria-label="Informasi rencana">
        <div><dt>Mata kuliah</dt><dd>{info.title || course.name}</dd></div>
        <div><dt>Kode mata kuliah</dt><dd>{info.code || course.code}</dd></div>
        {info.credits != null && <div><dt>Bobot</dt><dd>{info.credits} SKS</dd></div>}
        <div><dt>Jumlah minggu</dt><dd>{plan.weeks.length} minggu</dd></div>
      </dl>
      {info.description && <p className={styles.description}>{info.description}</p>}
      {outcomes.length > 0 && (
        <section aria-label="Capaian pembelajaran mata kuliah" className={styles.outcomes}>
          <h3>Capaian pembelajaran mata kuliah</h3>
          <TextList items={outcomes.map((item) => typeof item === 'string' ? item : [item.code, item.description].filter(Boolean).join(' — '))} />
        </section>
      )}

      {plan.weeks.length === 0 ? <EmptyState title="Rencana mingguan belum tersedia.">Belum ada minggu yang dapat ditampilkan pada rencana ini.</EmptyState> : (
        <>
          <div className={styles.tableWrap} role="region" aria-label="Tabel rencana mingguan" tabIndex={0}>
            <table className={`table ${styles.table}`}>
              <caption className={styles.caption}>Rencana pembelajaran mingguan</caption>
              <thead>
                <tr>
                  {['Minggu', 'Topik', 'Capaian pembelajaran', 'Tujuan pembelajaran', 'Metode mengajar', 'Aktivitas'].map((label) => <th key={label} scope="col">{label}</th>)}
                </tr>
              </thead>
              <tbody>
                {plan.weeks.map((week) => (
                  <tr key={week.week_number}>
                    <th scope="row">{week.week_number}</th>
                    <td>
                      <strong>{week.title || 'Topik belum tersedia.'}</strong>
                      <TextList items={week.topics} />
                      {week.note && <p className="note">{week.note}</p>}
                    </td>
                    <td><TextList items={week.learning_outcomes.map(outcomeText)} /></td>
                    <td><TextList items={week.objectives} /></td>
                    <td><TextList items={week.teaching_methods} /></td>
                    <td><Activities items={week.planned_activities} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ol className={styles.weekCards} aria-label="Rencana pembelajaran mingguan">
            {plan.weeks.map((week) => (
              <li key={week.week_number}>
                <article className={styles.weekCard} aria-label={`Minggu ${week.week_number}`}>
                  <h3>Minggu {week.week_number}: {week.title || 'Topik belum tersedia.'}</h3>
                  <dl className={styles.weekFields}>
                    <div><dt>Topik</dt><dd><TextList items={week.topics} /></dd></div>
                    <div><dt>Capaian pembelajaran</dt><dd><TextList items={week.learning_outcomes.map(outcomeText)} /></dd></div>
                    <div><dt>Tujuan pembelajaran</dt><dd><TextList items={week.objectives} /></dd></div>
                    <div><dt>Metode mengajar</dt><dd><TextList items={week.teaching_methods} /></dd></div>
                    <div><dt>Aktivitas</dt><dd><Activities items={week.planned_activities} /></dd></div>
                  </dl>
                  {week.note && <p className="note">{week.note}</p>}
                </article>
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
