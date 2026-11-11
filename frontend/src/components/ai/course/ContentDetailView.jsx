import { Badge } from '../../ui';
import MarkdownView from '../MarkdownView';
import { CONTENT_KIND, CONTENT_KIND_LABELS, VALIDATION_STATUS_META } from '../../../services/contentService';
import { validationFindings } from '../../../utils/contentReview';

const CHECK_LABELS = { schema: 'Struktur konten', sub_cpmk: 'Kesesuaian Sub-CPMK', resource_url: 'Tautan sumber', traceability: 'Keterlacakan', generation: 'Pembuatan konten' };
const checkLabel = (check) => CHECK_LABELS[check] ?? check;
const list = (value) => (Array.isArray(value) ? value.filter((item) => item != null && item !== '') : []);

function Section({ title, children }) {
  return (
    <section className="mt-4 first:mt-0">
      <h4 className="mb-1.5 text-[15px] font-semibold text-ink">{title}</h4>
      {children}
    </section>
  );
}

function TextList({ items }) {
  return <ul className="m-0 list-disc pl-5">{items.map((item, index) => <li key={index}>{item}</li>)}</ul>;
}

// Ilustrasi materi hanya dari host yang diisi backend: diagram (Kroki) dan foto berlisensi (Wikimedia Commons).
const TRUSTED_IMAGE = /^https:\/\/(kroki\.io|upload\.wikimedia\.org)\//;

/** Diagram atau foto satu section beserta keterangan dan atribusi lisensinya. */
function Illustration({ illustration }) {
  if (!illustration?.image_url || !TRUSTED_IMAGE.test(illustration.image_url)) return null;
  const credit = illustration.attribution;
  return (
    <figure className="my-4">
      <img
        src={illustration.image_url}
        alt={illustration.caption ?? ''}
        loading="lazy"
        className="mx-auto h-auto max-w-full rounded-md border border-line-subtle bg-white"
      />
      <figcaption className="mt-2 text-center text-xs text-muted">
        {illustration.caption}
        {credit && (
          <span className="block">
            {illustration.source_url?.startsWith('https://')
              ? <a href={illustration.source_url} target="_blank" rel="noreferrer">{credit}</a>
              : credit}
          </span>
        )}
      </figcaption>
    </figure>
  );
}

function LearningMaterial({ data, markdown }) {
  const objectives = list(data.learning_objectives);
  const sections = list(data.sections);
  return (
    <>
      {objectives.length > 0 && <Section title="Tujuan pembelajaran"><TextList items={objectives} /></Section>}
      {sections.length > 0 ? (
        sections.map((section, index) => (
          <Section key={index} title={section.heading || `Bagian ${index + 1}`}>
            <MarkdownView markdown={section.body_markdown} />
            <Illustration illustration={section.illustration} />
          </Section>
        ))
      ) : (
        markdown && <Section title="Isi materi"><MarkdownView markdown={markdown} /></Section>
      )}
    </>
  );
}

function Resource({ data, title }) {
  return (
    <>
      <Section title="Judul"><p>{title}</p></Section>
      {data.url && (
        <Section title="Tautan">
          <a href={data.url} target="_blank" rel="noreferrer" className="wrap-anywhere">{data.url}</a>
          {data.resource_kind && <span className="ml-2 text-sm text-muted">({data.resource_kind})</span>}
        </Section>
      )}
      {data.description && <Section title="Deskripsi"><p>{data.description}</p></Section>}
      {data.relevance_reason && <Section title="Alasan relevansi"><p>{data.relevance_reason}</p></Section>}
    </>
  );
}

function Assignment({ data }) {
  const outputs = list(data.expected_outputs);
  const rubric = list(data.rubric);
  return (
    <>
      <Section title="Instruksi"><MarkdownView markdown={data.instructions_markdown} /></Section>
      {outputs.length > 0 && <Section title="Luaran yang diharapkan"><TextList items={outputs} /></Section>}
      {rubric.length > 0 && (
        <Section title="Rubrik penilaian">
          <div className="max-w-full overflow-x-auto">
            <table className="table" aria-label="Rubrik penilaian">
              <thead><tr><th scope="col">Kriteria</th><th scope="col">Deskripsi</th><th scope="col">Bobot</th></tr></thead>
              <tbody>
                {rubric.map((row, index) => (
                  <tr key={index}>
                    <td>{row.criterion}</td>
                    <td>{row.description}</td>
                    <td>{row.weight_percent != null ? `${row.weight_percent}%` : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}
    </>
  );
}

function Quiz({ data }) {
  const questions = list(data.questions);
  const config = data.config ?? {};
  const settings = [
    config.time_limit_minutes != null && `Waktu ${config.time_limit_minutes} menit`,
    config.max_attempts != null && `${config.max_attempts} kali percobaan`,
    config.passing_score_percent != null && `Nilai lulus ${config.passing_score_percent}%`,
    config.shuffle_questions && 'Soal diacak',
  ].filter(Boolean);
  return (
    <>
      {data.description && <Section title="Deskripsi"><p>{data.description}</p></Section>}
      {settings.length > 0 && <p className="mt-2 text-sm text-muted">{settings.join(' · ')}</p>}
      <Section title={`Soal (${questions.length})`}>
        <ol className="m-0 grid list-decimal gap-4 pl-5">
          {questions.map((question, index) => (
            <li key={index}>
              <p className="font-medium">{question.question_text}</p>
              <ul className="mt-1 list-none pl-0" aria-label={`Opsi soal ${index + 1}`}>
                {list(question.options).map((option) => {
                  const correct = option.key === question.correct_option_key;
                  return (
                    <li key={option.key} className={correct ? 'font-semibold text-success' : ''}>
                      {option.key}. {option.text}{correct && <span className="sr-only"> (kunci jawaban)</span>}
                    </li>
                  );
                })}
              </ul>
              <p className="mt-1 text-sm"><strong>Kunci jawaban:</strong> {question.correct_option_key ?? '-'}</p>
              {question.explanation && <p className="mt-1 text-sm"><strong>Pembahasan:</strong> {question.explanation}</p>}
            </li>
          ))}
        </ol>
      </Section>
    </>
  );
}

/** Hasil validasi satu versi: status, skor, pemeriksaan, dan daftar temuan. */
export function ContentValidation({ validation }) {
  if (!validation) return <p className="text-sm text-muted">Konten ini belum divalidasi.</p>;
  const meta = VALIDATION_STATUS_META[validation.status] ?? { label: validation.status, tone: 'neutral' };
  const findings = validationFindings(validation);
  const checks = Object.entries(validation.checks ?? {});
  return (
    <div aria-label="Hasil validasi">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Badge tone={meta.tone}>{meta.label}</Badge>
        {validation.score != null && <span>Skor {Math.round(validation.score * 100)}%</span>}
        <span className="text-muted">{findings.length} temuan</span>
        {validation.retry_count > 0 && <span className="text-muted">· dicoba ulang {validation.retry_count} kali</span>}
      </div>
      {checks.length > 0 && (
        <ul className="mt-2 grid list-none gap-1 pl-0 text-sm">
          {checks.map(([check, result]) => (
            <li key={check}>
              <span aria-hidden="true">{result === 'PASSED' ? '✓' : '✕'}</span> {checkLabel(check)}:{' '}
              <span className={result === 'PASSED' ? 'text-success' : 'text-danger'}>{result === 'PASSED' ? 'lolos' : 'tidak lolos'}</span>
            </li>
          ))}
        </ul>
      )}
      {findings.length > 0 && (
        <ul className="mt-2 grid list-none gap-1 pl-0 text-sm" aria-label="Temuan validasi">
          {findings.map((finding, index) => (
            <li key={index} className={finding.severity === 'error' ? 'text-danger' : 'text-warning'}>
              <strong>{checkLabel(finding.check)}:</strong> {finding.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * Isi satu versi konten sesuai jenisnya (FE-17.2), seperti yang akan dilihat mahasiswa: materi (Markdown, tujuan,
 * Sub-CPMK), sumber belajar (judul, tautan, deskripsi, alasan relevansi), tugas (instruksi, luaran, rubrik), atau
 * kuis (soal, opsi, kunci, pembahasan).
 */
export default function ContentDetailView({ content }) {
  const data = content.content_data ?? {};
  const subCpmk = list(data.traceability?.sub_cpmk_codes ?? data.sub_cpmk_codes);
  return (
    <article aria-label={`Detail ${content.title}`}>
      <p className="text-sm text-muted">
        {CONTENT_KIND_LABELS[content.kind] ?? content.kind}
        {content.week_number != null && ` · Minggu ${content.week_number}`} · Versi {content.version}
      </p>
      <h3 className="mt-1 text-lg">{content.title}</h3>
      {subCpmk.length > 0 && <p className="mt-1 text-sm"><strong>Sub-CPMK:</strong> {subCpmk.join(', ')}</p>}
      {content.revision_notes && <p className="mt-2 rounded bg-warning-light px-3 py-2 text-sm text-warning"><strong>Catatan revisi:</strong> {content.revision_notes}</p>}

      <div className="mt-4">
        {content.kind === CONTENT_KIND.LEARNING_MATERIAL && <LearningMaterial data={data} markdown={content.content_markdown} />}
        {content.kind === CONTENT_KIND.RESOURCE && <Resource data={data} title={content.title} />}
        {content.kind === CONTENT_KIND.ASSIGNMENT && <Assignment data={data} />}
        {content.kind === CONTENT_KIND.QUIZ && <Quiz data={data} />}
      </div>

      <section className="mt-5 border-t border-line pt-4">
        <h4 className="mb-2 text-[15px] font-semibold">Hasil validasi</h4>
        <ContentValidation validation={content.validation} />
      </section>
    </article>
  );
}
