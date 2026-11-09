import { withToken } from '../../services/moodle/moodleClient';

// Purpose aktivitas (FEATURE_MOD_PURPOSE di mod/*/lib.php) menentukan warna ikon.
const PURPOSE = {
  attendance: 'administration',
  assign: 'assessment',
  quiz: 'assessment',
  workshop: 'assessment',
  lesson: 'content',
  forum: 'collaboration',
  glossary: 'collaboration',
  wiki: 'collaboration',
  data: 'collaboration',
  chat: 'communication',
  choice: 'communication',
  feedback: 'communication',
  survey: 'communication',
  bigbluebuttonbn: 'communication',
  page: 'content',
  book: 'content',
  resource: 'content',
  url: 'content',
  folder: 'content',
  label: 'content',
  h5pactivity: 'interactivecontent',
  scorm: 'interactivecontent',
};

// Rujukan source Moodle 5.3 (theme/boost/style/moodle.css): ukuran .activityiconcontainer, .small, .smaller.
const SIZES = { md: 'size-[52px]', sm: 'size-[42px]', xs: 'size-8' };

// Varian kotak (kartu aktivitas halaman kursus, seperti LMS ITK): latar warna purpose, glyph putih.
const BOX_BACKGROUND = {
  administration: 'bg-act-administration',
  assessment: 'bg-act-assessment',
  collaboration: 'bg-act-collaboration',
  communication: 'bg-act-communication',
  content: 'bg-act-content',
  interactivecontent: 'bg-act-interactive',
};

/**
 * Ikon aktivitas: glyph monologo diwarnai sesuai purpose, tanpa kotak latar.
 * Rujukan source Moodle 5.3: filter .act-icon--<purpose> disalin dari CSS tema Boost.
 * Dengan `boxed`: kotak berwarna sesuai purpose berisi glyph putih.
 */
export default function ActivityIcon({ modname, src, size = 'md', boxed = false }) {
  const purpose = PURPOSE[modname];
  const icon = src ?? `/moodle/mod/${modname}.svg`;
  if (boxed) {
    return (
      <span className={`grid size-10 shrink-0 place-items-center rounded-md ${BOX_BACKGROUND[purpose] ?? 'bg-act-other'}`} aria-hidden="true">
        <img src={withToken(icon)} alt="" className="size-6 brightness-0 invert" />
      </span>
    );
  }
  return (
    <span className={`${SIZES[size]} grid shrink-0 place-items-center`} aria-hidden="true">
      <img src={withToken(icon)} alt="" className={`size-full ${purpose ? `act-icon--${purpose}` : ''}`} />
    </span>
  );
}
