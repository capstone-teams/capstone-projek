import { useMemo } from 'react';
import DOMPurify from 'dompurify';
import { MOODLE_URL } from '../../services/config';
import { withToken } from '../../services/moodle/moodleClient';

/**
 * Menampilkan HTML dari Moodle (summary, intro, isi page).
 * HTML disanitasi dulu, lalu URL file pluginfile diberi token agar gambar/lampiran bisa dimuat.
 */
export default function MoodleHtml({ html, className = '' }) {
  const clean = useMemo(() => {
    if (!html) return '';
    const doc = new DOMParser().parseFromString(DOMPurify.sanitize(html), 'text/html');
    doc.querySelectorAll('img[src]').forEach((img) => img.setAttribute('src', withToken(img.getAttribute('src'))));
    doc.querySelectorAll('a[href]').forEach((a) => {
      a.setAttribute('href', withToken(new URL(a.getAttribute('href'), MOODLE_URL).href));
      a.setAttribute('target', '_blank');
      a.setAttribute('rel', 'noreferrer');
    });
    return doc.body.innerHTML;
  }, [html]);

  if (!clean) return null;
  // Aman: HTML sudah disanitasi DOMPurify di atas.
  return <div className={`prose-moodle ${className}`} dangerouslySetInnerHTML={{ __html: clean }} />;
}
