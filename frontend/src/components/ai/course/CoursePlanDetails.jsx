import { Badge, EmptyState } from '../../ui';

const ACTIVITY_LABELS = { learning_material: 'Materi', assignment: 'Tugas', quiz: 'Kuis' };
const COLUMNS = [
  { label: 'Minggu', className: 'w-[88px]' },
  { label: 'Topik', className: 'w-[22%]' },
  { label: 'Capaian pembelajaran', className: 'w-[23%]' },
  { label: 'Tujuan pembelajaran', className: 'w-[23%]' },
  { label: 'Metode mengajar' },
  { label: 'Aktivitas' },
];

function TextList({ items }) {
  return items.length ? (
    <ul className="my-1 list-disc pl-5">
      {items.map((item, index) => <li key={index} className="not-first:mt-1.5">{item}</li>)}
    </ul>
  ) : <span className="muted">Belum tersedia.</span>;
}

function InfoItem({ label, children }) {
  return <div className="min-w-0"><dt className="text-[13px] text-muted">{label}</dt><dd className="mt-1 font-semibold">{children}</dd></div>;
}

function WeekField({ label, children }) {
  return <div><dt className="mb-1 text-[13px] font-semibold text-ink-subtle">{label}</dt><dd>{children}</dd></div>;
}

function Activities({ items }) {
  return items.length ? (
    <div className="flex flex-wrap gap-1.5 [&>span]:wrap-anywhere [&>span]:whitespace-normal">
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
    <div className="min-w-0 wrap-anywhere">
      <dl className="mb-5 grid grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-4 max-lg:grid-cols-[minmax(0,1fr)] max-lg:gap-3" aria-label="Informasi rencana">
        <InfoItem label="Mata kuliah">{info.title || course.name}</InfoItem>
        <InfoItem label="Kode mata kuliah">{info.code || course.code}</InfoItem>
        {info.credits != null && <InfoItem label="Bobot">{info.credits} SKS</InfoItem>}
        <InfoItem label="Jumlah minggu">{plan.weeks.length} minggu</InfoItem>
      </dl>
      {info.description && <p className="mb-5">{info.description}</p>}
      {outcomes.length > 0 && (
        <section aria-label="Capaian pembelajaran mata kuliah" className="mb-6">
          <h3 className="mb-2 text-[16px]">Capaian pembelajaran mata kuliah</h3>
          <TextList items={outcomes.map((item) => typeof item === 'string' ? item : [item.code, item.description].filter(Boolean).join(' — '))} />
        </section>
      )}

      {plan.weeks.length === 0 ? <EmptyState title="Rencana mingguan belum tersedia.">Belum ada minggu yang dapat ditampilkan pada rencana ini.</EmptyState> : (
        <>
          <div className="max-w-full overflow-x-auto max-lg:hidden" role="region" aria-label="Tabel rencana mingguan" tabIndex={0}>
            <table className="table min-w-[1000px] table-fixed">
              <caption className="pb-3 text-left font-semibold">Rencana pembelajaran mingguan</caption>
              <thead>
                <tr>
                  {COLUMNS.map(({ label, className }) => <th key={label} scope="col" className={className}>{label}</th>)}
                </tr>
              </thead>
              <tbody>
                {plan.weeks.map((week) => (
                  <tr key={week.week_number}>
                    <th scope="row" className="w-[88px] border-b align-top">{week.week_number}</th>
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
          <ol className="m-0 hidden list-none p-0 max-lg:grid max-lg:gap-4" aria-label="Rencana pembelajaran mingguan">
            {plan.weeks.map((week) => (
              <li key={week.week_number} className="min-w-0">
                <article className="rounded-lg border border-line p-4" aria-label={`Minggu ${week.week_number}`}>
                  <h3 className="mb-4 text-[17px] leading-[1.5]">Minggu {week.week_number}: {week.title || 'Topik belum tersedia.'}</h3>
                  <dl className="m-0 grid gap-4">
                    <WeekField label="Topik"><TextList items={week.topics} /></WeekField>
                    <WeekField label="Capaian pembelajaran"><TextList items={week.learning_outcomes.map(outcomeText)} /></WeekField>
                    <WeekField label="Tujuan pembelajaran"><TextList items={week.objectives} /></WeekField>
                    <WeekField label="Metode mengajar"><TextList items={week.teaching_methods} /></WeekField>
                    <WeekField label="Aktivitas"><Activities items={week.planned_activities} /></WeekField>
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
