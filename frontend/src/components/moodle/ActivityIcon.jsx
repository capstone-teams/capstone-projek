import { withToken } from '../../services/moodle/moodleClient';

// Purpose aktivitas (FEATURE_MOD_PURPOSE di mod/*/lib.php) menentukan warna ikon.
const PURPOSE = {
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

/**
 * Ikon aktivitas: glyph monologo diwarnai sesuai purpose, tanpa kotak latar.
 * Rujukan source Moodle 5.3: filter .act-icon--<purpose> disalin dari CSS tema Boost.
 */
export default function ActivityIcon({ modname, src, size = 'md' }) {
  const purpose = PURPOSE[modname];
  const icon = src ?? `/moodle/mod/${modname}.svg`;
  return (
    <span className={`${SIZES[size]} grid shrink-0 place-items-center`} aria-hidden="true">
      <img src={withToken(icon)} alt="" className={`size-full ${purpose ? `act-icon--${purpose}` : ''}`} />
    </span>
  );
}
