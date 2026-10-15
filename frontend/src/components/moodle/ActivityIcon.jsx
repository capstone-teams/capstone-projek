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

// Ukuran .activityiconcontainer / .small / .smaller di theme/boost/style/moodle.css.
const SIZES = { md: 'size-[52px]', sm: 'size-[42px]', xs: 'size-8' };

/**
 * Ikon aktivitas gaya Moodle 5.3: glyph monologo diwarnai sesuai purpose
 * (filter .act-icon--<purpose> disalin dari CSS Moodle), tanpa kotak latar.
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
