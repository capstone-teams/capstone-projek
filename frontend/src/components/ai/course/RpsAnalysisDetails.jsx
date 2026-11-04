import { Alert, Badge, Card } from '../../ui';
import { SECTION_STATUS, danglingReferences, sectionStatuses } from '../../../utils/rpsAnalysis';

const STATUS_LABELS = {
  [SECTION_STATUS.COMPLETE]: 'Lengkap',
  [SECTION_STATUS.PARTIAL]: 'Belum lengkap',
  [SECTION_STATUS.NOT_FOUND]: 'Tidak ditemukan',
};
const ASSESSMENT_LABELS = { assignment: 'Tugas', quiz: 'Kuis', exam: 'Ujian', project: 'Proyek' };
const EXAM_LABELS = { uts: 'UTS', uas: 'UAS' };

const Missing = () => <span className="muted">–<span className="sr-only">tidak tercantum</span></span>;
const joined = (items) => (items.length ? items.join(', ') : <Missing />);

/** Judul bagian; status hanya ditandai bila bagian belum lengkap atau tidak ditemukan. */
function Part({ title, section, level = 'h3', children }) {
  const Heading = level;
  const label = STATUS_LABELS[section.status];
  return (
    <section aria-label={`${title}: ${label}`} className="not-first:mt-6">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <Heading className={level === 'h3' ? 'text-base' : 'text-lg'}>{title}</Heading>
        {section.status !== SECTION_STATUS.COMPLETE && (
          <Badge tone={section.status === SECTION_STATUS.NOT_FOUND ? 'danger' : 'warning'}>{label}</Badge>
        )}
      </div>
      {section.status === SECTION_STATUS.NOT_FOUND ? (
        <p className="muted">{title} tidak ditemukan pada RPS.</p>
      ) : (
        <>
          {section.notes.map((note) => <p key={note} className="mb-2 text-sm text-muted">{note}</p>)}
          {children}
        </>
      )}
    </section>
  );
}

function Codes({ ids, declared }) {
  if (!ids.length) return <Missing />;
  return ids.map((id, index) => (
    <span key={id}>
      {index > 0 && ', '}
      {id}
      {!declared.has(id) && <span className="text-danger"> (tidak tercantum pada RPS)</span>}
    </span>
  ));
}

function OutcomeTable({ items, relationLabel, relationField, declared }) {
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th scope="col" className="w-[110px]">Kode</th>
            <th scope="col">Deskripsi</th>
            <th scope="col" className="w-[160px]">{relationLabel}</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr key={item.id ?? index}>
              <th scope="row" className="align-top">{item.id ?? <Missing />}</th>
              <td className="align-top">{item.description}</td>
              <td className="align-top"><Codes ids={item[relationField]} declared={declared} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Indikator diambil dari deskripsi penilaian minggu itu: RPS Week Schema (content-schema §7) tidak punya field indikator.
const WEEK_COLUMNS = [
  ['Sub-CPMK', (week) => joined(week.sub_cpmk)],
  ['Materi', (week) => joined(week.topics)],
  ['Indikator', (week) => week.assessment?.description ?? <Missing />],
  ['Metode', (week) => joined(week.teaching_method)],
  ['Penilaian', (week) => (week.assessment?.type ? ASSESSMENT_LABELS[week.assessment.type] ?? week.assessment.type : <Missing />)],
  ['Bobot', (week) => (week.assessment?.weight_percent != null ? `${week.assessment.weight_percent}%` : <Missing />)],
];

const weekLabel = (week) => (EXAM_LABELS[week.week_type] ? `${week.week} (${EXAM_LABELS[week.week_type]})` : week.week);

function WeeklyPlan({ weeks }) {
  return (
    <>
      <div className="max-w-full overflow-x-auto max-lg:hidden" role="region" aria-label="Tabel rencana mingguan RPS" tabIndex={0}>
        <table className="table min-w-[900px]">
          <thead>
            <tr>
              <th scope="col" className="w-[90px]">Minggu</th>
              {WEEK_COLUMNS.map(([label]) => <th key={label} scope="col" className="whitespace-nowrap">{label}</th>)}
            </tr>
          </thead>
          <tbody>
            {weeks.map((week) => (
              <tr key={week.week}>
                <th scope="row" className="align-top">{weekLabel(week)}</th>
                {WEEK_COLUMNS.map(([label, render]) => <td key={label} className="align-top">{render(week)}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ol className="m-0 hidden list-none flex-col p-0 max-lg:flex" aria-label="Rencana mingguan RPS">
        {weeks.map((week) => (
          <li key={week.week} className="border-b border-line py-3 last:border-b-0">
            <h4 className="mb-1 font-semibold">Minggu {weekLabel(week)}</h4>
            <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-sm">
              {WEEK_COLUMNS.map(([label, render]) => (
                <div key={label} className="contents">
                  <dt className="text-muted">{label}</dt>
                  <dd className="wrap-anywhere">{render(week)}</dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ol>
    </>
  );
}

function Assessments({ items }) {
  const total = items.every((item) => item.weight_percent != null) ? items.reduce((sum, item) => sum + item.weight_percent, 0) : null;
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th scope="col">Komponen</th>
            <th scope="col">Minggu</th>
            <th scope="col" className="text-right">Bobot</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr key={item.id ?? index}>
              <td>{item.description ?? ASSESSMENT_LABELS[item.type] ?? item.type ?? '–'}</td>
              <td>{item.week ?? '–'}</td>
              <td className="text-right">{item.weight_percent != null ? `${item.weight_percent}%` : '–'}</td>
            </tr>
          ))}
        </tbody>
        {total != null && (
          <tfoot>
            <tr>
              <th scope="row" colSpan={2} className="text-right">Total</th>
              <td className={`text-right font-semibold ${total === 100 ? '' : 'text-danger'}`}>{total}%</td>
            </tr>
          </tfoot>
        )}
      </table>
    </div>
  );
}

/** Hasil analisis RPS (Proposal §3.7.5). `analysis` dari normalizeRpsAnalysis(). */
export default function RpsAnalysisDetails({ analysis }) {
  const sections = sectionStatuses(analysis, danglingReferences(analysis));
  const { course } = analysis;
  const warnings = analysis.extraction?.warnings ?? [];
  const ids = (items) => new Set(items.map((item) => item.id).filter(Boolean));

  return (
    <div className="stack">
      {warnings.length > 0 && (
        <Alert tone="warning" title="Catatan dari proses ekstraksi">
          <ul className="mt-1 list-disc pl-5">{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
        </Alert>
      )}

      <Card>
        <Part title="Identitas mata kuliah" section={sections.identity} level="h2">
          <dl className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-4">
            {[['Mata kuliah', course.name], ['Kode', course.code], ['Bobot', course.credits != null ? `${course.credits} SKS` : null], ['Semester', course.semester]].map(([label, value]) => (
              <div key={label}>
                <dt className="text-[13px] text-muted">{label}</dt>
                <dd className="mt-1 font-semibold">{value ?? <span className="font-normal text-muted">Tidak tercantum</span>}</dd>
              </div>
            ))}
          </dl>
          {course.description && <p className="mt-4">{course.description}</p>}
        </Part>
      </Card>

      <Card title="Capaian pembelajaran">
        <Part title="CPL" section={sections.cpl}>
          <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
            {analysis.cpl.map((cpl, index) => (
              <li key={cpl.id ?? index}><strong className="mr-2">{cpl.id}</strong>{cpl.description}</li>
            ))}
          </ul>
        </Part>
        <Part title="CPMK" section={sections.cpmk}>
          <OutcomeTable items={analysis.cpmk} relationLabel="CPL" relationField="cpl_ids" declared={ids(analysis.cpl)} />
        </Part>
        <Part title="Sub-CPMK" section={sections.subCpmk}>
          <OutcomeTable items={analysis.subCpmk} relationLabel="CPMK" relationField="cpmk_ids" declared={ids(analysis.cpmk)} />
        </Part>
      </Card>

      <Card>
        <Part title="Rencana mingguan" section={sections.weeks} level="h2">
          <WeeklyPlan weeks={analysis.weeks} />
        </Part>
      </Card>

      <div className="grid grid-cols-[minmax(0,1fr)] gap-5 lg:grid-cols-2">
        <Card>
          <Part title="Penilaian" section={sections.assessments} level="h2">
            <Assessments items={analysis.assessments} />
          </Part>
        </Card>
        <Card>
          <Part title="Referensi" section={sections.references} level="h2">
            <ol className="m-0 flex list-decimal flex-col gap-2 pl-5">
              {analysis.references.map((ref, index) => (
                <li key={ref.id ?? index} className="wrap-anywhere">
                  {ref.citation}
                  {[ref.authors, ref.year, ref.source].some(Boolean) && <span className="text-muted"> — {[ref.authors, ref.year, ref.source].filter(Boolean).join(', ')}</span>}
                </li>
              ))}
            </ol>
          </Part>
        </Card>
      </div>
    </div>
  );
}
