import { useEffect, useRef, useState } from 'react';
import { Modal } from '../../ui';
import { countWords } from '../../../utils/assignSubmission';

// Ikon toolbar gaya TinyMCE (oxide) yang dipakai editor Moodle; garis 24×24.
const ICONS = {
  undo: 'M9 14 4 9l5-5M4 9h10.5a5.5 5.5 0 0 1 0 11H11',
  redo: 'm15 14 5-5-5-5M20 9H9.5a5.5 5.5 0 0 0 0 11H13',
  image: 'M4 5h16v14H4zM4 16l5-5 4 4 2-2 5 5M15.5 9.5h.01',
  media: 'M4 5h16v14H4zM10 9v6l5-3z',
  link: 'M10 14a4 4 0 0 0 5.66 0l3-3a4 4 0 0 0-5.66-5.66l-1 1M14 10a4 4 0 0 0-5.66 0l-3 3a4 4 0 0 0 5.66 5.66l1-1',
  unlink: 'M10 14a4 4 0 0 0 5.66 0l3-3a4 4 0 0 0-5.66-5.66l-1 1M14 10a4 4 0 0 0-5.66 0l-3 3a4 4 0 0 0 5.66 5.66l1-1M4 4l16 16',
  fullscreen: 'M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5',
  more: 'M6 12h.01M12 12h.01M18 12h.01',
  bullist: 'M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01',
  numlist: 'M10 6h10M10 12h10M10 18h10M4 4.5h1.5V9M4 15h2.5L4 19h2.5',
  removeformat: 'M6 5h12M12 5l-3 14M4 20 20 4',
};

function Icon({ name }) {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={ICONS[name]} />
    </svg>
  );
}

const exec = (command, value) => document.execCommand?.(command, false, value);

/** Menu bar TinyMCE: Edit, View, Insert, Format, Tools, Table, Help. */
function MenuBar({ menus }) {
  const [open, setOpen] = useState(null);
  const rootRef = useRef(null);

  useEffect(() => {
    if (open == null) return undefined;
    rootRef.current?.querySelector('[role="menu"] [role="menuitem"]')?.focus();
    const outside = (event) => !rootRef.current?.contains(event.target) && setOpen(null);
    document.addEventListener('mousedown', outside);
    return () => document.removeEventListener('mousedown', outside);
  }, [open]);

  const onKeyDown = (event) => {
    const items = [...rootRef.current.querySelectorAll('[role="menu"] [role="menuitem"]')];
    const index = items.indexOf(document.activeElement);
    const focus = (i) => { event.preventDefault(); items[(i + items.length) % items.length]?.focus(); };
    if (event.key === 'Escape') { event.preventDefault(); rootRef.current.querySelectorAll('[aria-haspopup]')[open]?.focus(); setOpen(null); }
    else if (event.key === 'ArrowDown') focus(index + 1);
    else if (event.key === 'ArrowUp') focus(index - 1);
    else if (event.key === 'ArrowRight') { event.preventDefault(); setOpen((open + 1) % menus.length); }
    else if (event.key === 'ArrowLeft') { event.preventDefault(); setOpen((open - 1 + menus.length) % menus.length); }
    else if (event.key === 'Tab') setOpen(null);
  };

  return (
    <div ref={rootRef} role="menubar" aria-label="Menu editor" className="relative flex flex-wrap gap-0.5 px-2 pt-1.5" onKeyDown={onKeyDown}>
      {menus.map((menu, index) => (
        <div key={menu.label} className="relative">
          <button
            type="button"
            aria-haspopup="menu"
            aria-expanded={open === index}
            className={`cursor-pointer rounded px-2 py-1 text-[13px] text-ink hover:bg-line-subtle ${open === index ? 'bg-line-subtle' : ''}`}
            onClick={() => setOpen(open === index ? null : index)}
          >
            {menu.label}
          </button>
          {open === index && (
            <div role="menu" aria-label={menu.label} className="absolute top-full left-0 z-30 mt-1 min-w-48 rounded-md border border-line bg-white py-1 shadow-lg">
              {menu.items.map((item) => (
                <button
                  key={item.label}
                  type="button"
                  role="menuitem"
                  className="flex w-full cursor-pointer items-center justify-between gap-6 px-3 py-1.5 text-left text-sm hover:bg-line-subtle focus-visible:bg-line-subtle focus-visible:outline-none"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => { setOpen(null); item.run(); }}
                >
                  {item.label}
                  {item.shortcut && <span className="text-xs text-muted">{item.shortcut}</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function ToolButton({ label, onClick, active, children }) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      aria-pressed={active}
      className={`grid h-8 min-w-8 cursor-pointer place-items-center rounded px-1 text-ink hover:bg-line-subtle ${active ? 'bg-line-subtle' : ''}`}
      // Jangan pindahkan fokus dari area teks agar seleksi tetap ada.
      onMouseDown={(event) => event.preventDefault()}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

const DIALOGS = {
  link: { title: 'Insert/edit link', fields: [['url', 'URL'], ['text', 'Text to display']] },
  image: { title: 'Insert image', fields: [['url', 'Image URL'], ['alt', 'Describe this image for someone who cannot see it']] },
  media: { title: 'Insert media', fields: [['url', 'Media URL']] },
};

const SHORTCUTS = [['Bold', 'Ctrl+B'], ['Italic', 'Ctrl+I'], ['Underline', 'Ctrl+U'], ['Undo', 'Ctrl+Z'], ['Redo', 'Ctrl+Y'], ['Select all', 'Ctrl+A']];

/**
 * Editor teks seperti TinyMCE di Moodle (Online text): menu bar, toolbar, area isi,
 * dan status bar berisi jalur elemen serta jumlah kata. Nilai berupa HTML.
 */
export default function MoodleEditor({ id, labelId, initialValue = '', onChange, invalid, describedBy }) {
  const contentRef = useRef(null);
  const rangeRef = useRef(null);
  const [words, setWords] = useState(() => countWords(initialValue));
  const [plain, setPlain] = useState(() => new DOMParser().parseFromString(initialValue, 'text/html').body.textContent ?? '');
  const [path, setPath] = useState(['p']);
  const [fullscreen, setFullscreen] = useState(false);
  const [more, setMore] = useState(false);
  const [dialog, setDialog] = useState(null);
  const [fields, setFields] = useState({});
  const [, setTick] = useState(0);

  useEffect(() => {
    contentRef.current.innerHTML = initialValue || '<p><br></p>';
    // Isi awal hanya dipasang sekali; selanjutnya area teks yang memegang nilainya.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const update = () => {
      const selection = document.getSelection();
      const root = contentRef.current;
      if (!selection?.anchorNode || !root?.contains(selection.anchorNode)) return;
      const tags = [];
      for (let node = selection.anchorNode; node && node !== root; node = node.parentNode) {
        if (node.nodeType === 1) tags.unshift(node.nodeName.toLowerCase());
      }
      setPath(tags.length ? tags : ['p']);
      setTick((tick) => tick + 1);
    };
    document.addEventListener('selectionchange', update);
    return () => document.removeEventListener('selectionchange', update);
  }, []);

  const emit = () => {
    const html = contentRef.current.innerHTML;
    const text = contentRef.current.textContent;
    setWords(countWords(text));
    setPlain(text);
    onChange(text.trim() ? html : '');
  };
  const doCommand = (command, value) => {
    contentRef.current.focus();
    exec(command, value);
    emit();
  };
  const isActive = (command) => {
    try {
      return document.queryCommandState?.(command) ?? false;
    } catch {
      return false;
    }
  };

  const openDialog = (name) => {
    const selection = document.getSelection();
    rangeRef.current = selection?.rangeCount && contentRef.current.contains(selection.anchorNode) ? selection.getRangeAt(0) : null;
    setFields({ text: selection?.toString() ?? '' });
    setDialog(name);
  };
  const restoreRange = () => {
    contentRef.current.focus();
    if (rangeRef.current) {
      const selection = document.getSelection();
      selection.removeAllRanges();
      selection.addRange(rangeRef.current);
    }
  };
  const escape = (text) => text.replace(/[&<>"]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]);
  // Bukan <form>: editor berada di dalam formulir pengumpulan, dan submit form bersarang ikut ke formulir luar.
  const insertFromDialog = () => {
    const url = (fields.url ?? '').trim();
    setDialog(null);
    if (!url || !/^(https?:|mailto:|\/)/i.test(url)) return;
    restoreRange();
    if (dialog === 'link') {
      const text = (fields.text ?? '').trim();
      if (document.getSelection()?.toString()) exec('createLink', url);
      else exec('insertHTML', `<a href="${escape(url)}">${escape(text || url)}</a>`);
    } else if (dialog === 'image') {
      exec('insertHTML', `<img src="${escape(url)}" alt="${escape(fields.alt ?? '')}">`);
    } else {
      exec('insertHTML', `<video controls src="${escape(url)}"></video>`);
    }
    emit();
  };

  const menus = [
    { label: 'Edit', items: [
      { label: 'Undo', shortcut: 'Ctrl+Z', run: () => doCommand('undo') },
      { label: 'Redo', shortcut: 'Ctrl+Y', run: () => doCommand('redo') },
      { label: 'Select all', shortcut: 'Ctrl+A', run: () => doCommand('selectAll') },
    ] },
    { label: 'View', items: [{ label: 'Fullscreen', run: () => setFullscreen((value) => !value) }] },
    { label: 'Insert', items: [
      { label: 'Image...', run: () => openDialog('image') },
      { label: 'Media...', run: () => openDialog('media') },
      { label: 'Link...', shortcut: 'Ctrl+K', run: () => openDialog('link') },
      { label: 'Horizontal line', run: () => doCommand('insertHorizontalRule') },
    ] },
    { label: 'Format', items: [
      { label: 'Bold', shortcut: 'Ctrl+B', run: () => doCommand('bold') },
      { label: 'Italic', shortcut: 'Ctrl+I', run: () => doCommand('italic') },
      { label: 'Underline', shortcut: 'Ctrl+U', run: () => doCommand('underline') },
      { label: 'Strikethrough', run: () => doCommand('strikeThrough') },
      { label: 'Superscript', run: () => doCommand('superscript') },
      { label: 'Subscript', run: () => doCommand('subscript') },
      { label: 'Paragraph', run: () => doCommand('formatBlock', 'p') },
      { label: 'Heading 3', run: () => doCommand('formatBlock', 'h3') },
      { label: 'Heading 4', run: () => doCommand('formatBlock', 'h4') },
      { label: 'Clear formatting', run: () => doCommand('removeFormat') },
    ] },
    { label: 'Tools', items: [{ label: 'Word count', run: () => setDialog('wordcount') }] },
    { label: 'Table', items: [{
      label: 'Insert table (2 × 2)',
      run: () => doCommand('insertHTML', '<table><tbody><tr><td><br></td><td><br></td></tr><tr><td><br></td><td><br></td></tr></tbody></table><p><br></p>'),
    }] },
    { label: 'Help', items: [{ label: 'Keyboard shortcuts', run: () => setDialog('shortcuts') }] },
  ];

  const onKeyDown = (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      openDialog('link');
    }
  };

  return (
    <div
      className={`flex flex-col rounded-lg border bg-white shadow-[0_2px_2px_-2px_rgba(34,47,62,0.1),0_8px_8px_-4px_rgba(34,47,62,0.07)] ${invalid ? 'border-danger' : 'border-line'} ${fullscreen ? 'fixed inset-0 z-50 rounded-none' : ''}`}
    >
      <div className="border-b border-line shadow-[0_2px_2px_-2px_rgba(34,47,62,0.1)]">
        <MenuBar menus={menus} />
        <div role="toolbar" aria-label="Toolbar editor" className="flex flex-wrap items-center gap-0.5 px-2 py-1">
          <ToolButton label="Undo" onClick={() => doCommand('undo')}><Icon name="undo" /></ToolButton>
          <ToolButton label="Redo" onClick={() => doCommand('redo')}><Icon name="redo" /></ToolButton>
          <span className="mx-1 h-6 w-px bg-line" aria-hidden="true" />
          <ToolButton label="Bold" active={isActive('bold')} onClick={() => doCommand('bold')}><b className="font-serif text-[15px]">B</b></ToolButton>
          <ToolButton label="Italic" active={isActive('italic')} onClick={() => doCommand('italic')}><i className="font-serif text-[15px]">I</i></ToolButton>
          <span className="mx-1 h-6 w-px bg-line" aria-hidden="true" />
          <ToolButton label="Image" onClick={() => openDialog('image')}><Icon name="image" /></ToolButton>
          <ToolButton label="Multimedia" onClick={() => openDialog('media')}><Icon name="media" /></ToolButton>
          <span className="mx-1 h-6 w-px bg-line" aria-hidden="true" />
          <ToolButton label="Link" onClick={() => openDialog('link')}><Icon name="link" /></ToolButton>
          <ToolButton label="Unlink" onClick={() => doCommand('unlink')}><Icon name="unlink" /></ToolButton>
          <span className="mx-1 h-6 w-px bg-line" aria-hidden="true" />
          <ToolButton label="Full screen" active={fullscreen} onClick={() => setFullscreen((value) => !value)}><Icon name="fullscreen" /></ToolButton>
          <ToolButton label="Reveal or hide additional toolbar items" active={more} onClick={() => setMore((value) => !value)}><Icon name="more" /></ToolButton>
        </div>
        {more && (
          <div role="toolbar" aria-label="Toolbar tambahan" className="flex flex-wrap items-center gap-0.5 border-t border-line px-2 py-1">
            <ToolButton label="Underline" active={isActive('underline')} onClick={() => doCommand('underline')}><u className="font-serif text-[15px]">U</u></ToolButton>
            <ToolButton label="Strikethrough" active={isActive('strikeThrough')} onClick={() => doCommand('strikeThrough')}><s className="font-serif text-[15px]">S</s></ToolButton>
            <ToolButton label="Bullet list" onClick={() => doCommand('insertUnorderedList')}><Icon name="bullist" /></ToolButton>
            <ToolButton label="Numbered list" onClick={() => doCommand('insertOrderedList')}><Icon name="numlist" /></ToolButton>
            <ToolButton label="Clear formatting" onClick={() => doCommand('removeFormat')}><Icon name="removeformat" /></ToolButton>
          </div>
        )}
      </div>
      <div
        ref={contentRef}
        id={id}
        role="textbox"
        aria-multiline="true"
        aria-labelledby={labelId}
        aria-invalid={invalid ? 'true' : undefined}
        aria-describedby={describedBy}
        contentEditable
        suppressContentEditableWarning
        tabIndex={0}
        className={`prose-moodle overflow-auto px-4 py-3 text-[15px] outline-none ${fullscreen ? 'flex-1' : 'min-h-56 resize-y'}`}
        onInput={emit}
        onKeyDown={onKeyDown}
      />
      <div className="flex items-center justify-between gap-3 border-t border-line px-3 py-1 text-xs text-muted">
        <span aria-label="Jalur elemen">{path.join(' » ')}</span>
        <span aria-live="polite">{words} {words === 1 ? 'word' : 'words'}</span>
      </div>

      <Modal open={['link', 'image', 'media'].includes(dialog)} title={DIALOGS[dialog]?.title} onClose={() => setDialog(null)}
        footer={<>
          <button type="button" className="btn" onClick={() => setDialog(null)}>Cancel</button>
          <button type="button" className="btn btn--primary" onClick={insertFromDialog}>Save</button>
        </>}
      >
        <div className="form">
          {DIALOGS[dialog]?.fields.map(([key, label], index) => (
            <label key={key} className="flex flex-col gap-1.5 text-sm font-semibold">
              {label}
              <input
                value={fields[key] ?? ''}
                autoFocus={index === 0}
                onChange={(event) => setFields({ ...fields, [key]: event.target.value })}
                onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); insertFromDialog(); } }}
              />
            </label>
          ))}
        </div>
      </Modal>
      <Modal open={dialog === 'wordcount'} title="Word count" onClose={() => setDialog(null)}>
        <table className="table">
          <tbody>
            <tr><th className="!font-normal">Words</th><td>{words}</td></tr>
            <tr><th className="!font-normal">Characters</th><td>{plain.length}</td></tr>
            <tr><th className="!font-normal">Characters (no spaces)</th><td>{plain.replace(/\s/g, '').length}</td></tr>
          </tbody>
        </table>
      </Modal>
      <Modal open={dialog === 'shortcuts'} title="Keyboard shortcuts" onClose={() => setDialog(null)}>
        <table className="table">
          <tbody>
            {SHORTCUTS.map(([action, keys]) => <tr key={action}><th className="!font-normal">{action}</th><td><kbd>{keys}</kbd></td></tr>)}
          </tbody>
        </table>
      </Modal>
    </div>
  );
}
