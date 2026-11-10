import { useMemo } from 'react';
import DOMPurify from 'dompurify';
import { marked } from 'marked';

/** Markdown hasil agent dirender seperti di halaman kursus; HTML hasil marked disanitasi DOMPurify. */
export default function MarkdownView({ markdown, className = '' }) {
  const html = useMemo(() => (markdown ? DOMPurify.sanitize(marked.parse(String(markdown), { async: false })) : ''), [markdown]);
  if (!html) return null;
  // Aman: HTML sudah disanitasi DOMPurify di atas.
  return <div className={`prose-moodle ${className}`} dangerouslySetInnerHTML={{ __html: html }} />;
}
