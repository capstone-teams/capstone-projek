// Utilitas membaca isi HTML activity (mis. Page materi hasil Generator AI) untuk pratinjau dan tampilan artikel.

const WORDS_PER_MINUTE = 200;

function parse(html) {
  return new DOMParser().parseFromString(String(html ?? ''), 'text/html');
}

/** Teks polos dari HTML, spasi dirapikan. */
export function htmlToText(html) {
  if (!html) return '';
  return (parse(html).body.textContent ?? '').replace(/\s+/g, ' ').trim();
}

/** Perkiraan waktu baca (menit, minimal 1) untuk teks berbahasa Indonesia. */
export function readingMinutes(text) {
  const words = String(text ?? '').split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.round(words / WORDS_PER_MINUTE));
}

const slug = (text, index) => {
  const base = String(text ?? '')
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .slice(0, 48);
  return `bagian-${index + 1}${base ? `-${base}` : ''}`;
};

/**
 * Siapkan HTML untuk dibaca sebagai artikel: heading h2/h3 diberi id agar dapat ditautkan dari daftar isi.
 * Mengembalikan { html, headings: [{ id, text, level }] }. HTML tetap disanitasi oleh MoodleHtml saat dirender.
 */
export function withHeadingAnchors(html) {
  if (!html) return { html: '', headings: [] };
  const doc = parse(html);
  const headings = [...doc.body.querySelectorAll('h2, h3')].map((node, index) => {
    const text = (node.textContent ?? '').replace(/\s+/g, ' ').trim();
    const id = node.id || slug(text, index);
    node.id = id;
    return { id, text, level: node.tagName === 'H2' ? 2 : 3 };
  }).filter((heading) => heading.text);
  return { html: doc.body.innerHTML, headings };
}
