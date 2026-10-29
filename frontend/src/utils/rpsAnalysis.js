// Hasil GET /rps/{id}/analysis (design-api §6.4): RPS Structured Data, content-schema §6.2/§7.
// Backend belum mengirim status per bagian, jadi status diturunkan dari isi datanya.

export const SECTION_STATUS = { COMPLETE: 'complete', PARTIAL: 'partial', NOT_FOUND: 'not_found' };

const list = (value) => (Array.isArray(value) ? value : []);

export function normalizeRpsAnalysis(response) {
  const data = response?.data ?? {};
  return {
    analyzedAt: response?.analyzed_at ?? null,
    course: data.course ?? {},
    cpl: list(data.cpl),
    cpmk: list(data.cpmk).map((item) => ({ ...item, cpl_ids: list(item.cpl_ids) })),
    subCpmk: list(data.sub_cpmk).map((item) => ({ ...item, cpmk_ids: list(item.cpmk_ids) })),
    topics: list(data.topics),
    media: list(data.media),
    weeks: list(data.weeks)
      .map((week) => ({
        ...week,
        week_type: week.week_type ?? 'regular',
        topics: list(week.topics),
        cpmk: list(week.cpmk),
        sub_cpmk: list(week.sub_cpmk),
        teaching_method: list(week.teaching_method),
        media: list(week.media),
        assessment: week.assessment ?? null,
      }))
      .sort((a, b) => a.week - b.week),
    assessments: list(data.assessments),
    references: list(data.references),
    extraction: data.extraction ?? null,
  };
}

/** Sama dengan RPSStructuredData.validate_references di backend; daftar sasaran kosong dilewati. */
export function danglingReferences(analysis) {
  const ids = (items) => new Set(items.map((item) => item.id).filter(Boolean));
  const names = (items) => new Set(items.map((item) => item.name).filter(Boolean));
  const findings = [];
  const check = (source, field, values, declared, week = null) => {
    if (!declared.size) return;
    new Set(values).forEach((value) => !declared.has(value) && findings.push({ source, field, value, week }));
  };
  check('cpmk', 'cpl_ids', analysis.cpmk.flatMap((item) => item.cpl_ids), ids(analysis.cpl));
  check('sub_cpmk', 'cpmk_ids', analysis.subCpmk.flatMap((item) => item.cpmk_ids), ids(analysis.cpmk));
  analysis.weeks.forEach((week) => {
    check('week', 'cpmk', week.cpmk, ids(analysis.cpmk), week.week);
    check('week', 'sub_cpmk', week.sub_cpmk, ids(analysis.subCpmk), week.week);
    check('week', 'topics', week.topics, names(analysis.topics), week.week);
    check('week', 'media', week.media, names(analysis.media), week.week);
  });
  return findings;
}

const TARGET_LABELS = { cpl_ids: 'CPL', cpmk_ids: 'CPMK', cpmk: 'CPMK', sub_cpmk: 'Sub-CPMK', topics: 'materi', media: 'media' };
const SOURCE_LABELS = { cpmk: 'CPMK', sub_cpmk: 'Sub-CPMK' };

function describe({ source, field, value, week }) {
  return `${SOURCE_LABELS[source] ?? `Minggu ${week}`} merujuk ${TARGET_LABELS[field]} "${value}" yang tidak tercantum pada RPS.`;
}

const result = (empty, notes) => ({
  status: empty ? SECTION_STATUS.NOT_FOUND : notes.length ? SECTION_STATUS.PARTIAL : SECTION_STATUS.COMPLETE,
  notes: empty ? [] : notes,
});

/** not_found = bagian kosong; partial = terisi tetapi ada yang kurang (beserta catatannya). */
export function sectionStatuses(analysis, dangling = danglingReferences(analysis)) {
  const { course } = analysis;
  const identity = { name: 'nama', code: 'kode', credits: 'SKS', semester: 'semester' };
  const missing = Object.keys(identity).filter((key) => course[key] == null || course[key] === '').map((key) => identity[key]);
  const regularWeeks = analysis.weeks.filter((week) => week.week_type === 'regular');
  const gaps = (field, label) => {
    const weeks = regularWeeks.filter((week) => !week[field].length).map((week) => week.week);
    return weeks.length ? [`${label} tidak ditemukan pada minggu ${weeks.join(', ')}.`] : [];
  };
  const references = (source) => dangling.filter((item) => item.source === source).map(describe);

  return {
    identity: result(missing.length === 4, missing.length ? [`Tidak tercantum: ${missing.join(', ')}.`] : []),
    cpl: result(!analysis.cpl.length, []),
    cpmk: result(!analysis.cpmk.length, [
      ...(analysis.cpmk.some((item) => !item.cpl_ids.length) ? ['Sebagian CPMK tidak dikaitkan dengan CPL.'] : []),
      ...references('cpmk'),
    ]),
    subCpmk: result(!analysis.subCpmk.length, [
      ...(analysis.subCpmk.some((item) => !item.cpmk_ids.length) ? ['Sebagian Sub-CPMK tidak dikaitkan dengan CPMK.'] : []),
      ...references('sub_cpmk'),
    ]),
    weeks: result(!analysis.weeks.length, [
      ...gaps('topics', 'Materi'),
      ...gaps('sub_cpmk', 'Sub-CPMK'),
      ...gaps('teaching_method', 'Metode pembelajaran'),
      ...references('week'),
    ]),
    assessments: result(
      !analysis.assessments.length,
      analysis.assessments.some((item) => item.weight_percent == null) ? ['Sebagian komponen penilaian tidak mencantumkan bobot.'] : [],
    ),
    references: result(!analysis.references.length, []),
  };
}
