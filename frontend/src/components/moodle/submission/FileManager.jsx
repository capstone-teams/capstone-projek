import { useRef, useState } from 'react';
import { Modal } from '../../ui';
import { withToken } from '../../../services/moodle/moodleClient';
import { formatLimit } from '../../../utils/assignSubmission';
import { formatFileSize, formatUnixDateTime } from '../../../utils/format';

/*
 * File manager seperti form element `filemanager` Moodle (Add..., Create folder, tampilan
 * ikon/detail/pohon, jalur folder, dan area seret-dan-lepas). Isinya dikendalikan induk:
 * value = { entries: [{ key, filepath, filename, filesize, timemodified, file?, fileurl? }], folders: ['/a/'] }.
 */

const VIEWS = [
  ['icons', 'Display folder with file icons', 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z'],
  ['details', 'Display folder with file details', 'M4 6h16M4 12h16M4 18h16'],
  ['tree', 'Display folder as file tree', 'M3 6h7l2 2h9v11H3z'],
];

let seq = 0;
const nextKey = () => `f${++seq}`;

function FileIcon({ name, size = 40 }) {
  const ext = (name.split('.').pop() ?? '').slice(0, 4).toUpperCase();
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
      <path d="M9 3h16l8 8v26H9z" fill="#fff" stroke="#8f959e" strokeWidth="1.5" />
      <path d="M25 3v8h8" fill="none" stroke="#8f959e" strokeWidth="1.5" />
      {ext && <text x="21" y="29" textAnchor="middle" fontSize="8" fontWeight="700" fill="#0f6cbf">{ext}</text>}
    </svg>
  );
}

function FolderIcon({ size = 40 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
      <path d="M4 9h12l3 3h17v20H4z" fill="#f2c94c" stroke="#c99a15" strokeWidth="1.2" />
    </svg>
  );
}

// Nama ganda diberi akhiran seperti Moodle: "laporan (1).pdf".
function uniqueName(name, taken) {
  if (!taken.has(name)) return name;
  const dot = name.lastIndexOf('.');
  const [base, ext] = dot > 0 ? [name.slice(0, dot), name.slice(dot)] : [name, ''];
  for (let n = 1; ; n += 1) if (!taken.has(`${base} (${n})${ext}`)) return `${base} (${n})${ext}`;
}

const childFolders = (folders, path) => folders.filter((f) => f !== path && f.startsWith(path) && !f.slice(path.length, -1).includes('/'));
const folderName = (path) => path.slice(0, -1).split('/').pop();
const TOOL_BUTTON = 'grid size-7 cursor-pointer place-items-center rounded border border-line bg-line-subtle text-ink hover:bg-line';

function Tree({ at, folders, entries, onOpen }) {
  return (
    <ul className="ml-4 flex flex-col gap-1">
      {childFolders(folders, at).map((folder) => (
        <li key={folder}>
          <button type="button" className="flex cursor-pointer items-center gap-1.5 hover:underline" onClick={() => onOpen({ folder, filename: folderName(folder) }, true)}>
            <FolderIcon size={20} />{folderName(folder)}
          </button>
          <Tree at={folder} folders={folders} entries={entries} onOpen={onOpen} />
        </li>
      ))}
      {entries.filter((entry) => entry.filepath === at).map((entry) => (
        <li key={entry.key}>
          <button type="button" className="flex cursor-pointer items-center gap-1.5 hover:underline" onClick={() => onOpen(entry)}>
            <FileIcon name={entry.filename} size={20} />{entry.filename}
          </button>
        </li>
      ))}
    </ul>
  );
}

export default function FileManager({ value, onChange, maxFiles, maxBytes, labelId }) {
  const inputRef = useRef(null);
  const [view, setView] = useState('icons');
  const [path, setPath] = useState('/');
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(null);
  const [newName, setNewName] = useState('');
  const [creating, setCreating] = useState(false);
  const { entries, folders } = value;

  const filesIn = (p) => entries.filter((entry) => entry.filepath === p);
  const namesIn = (p) => new Set([...filesIn(p).map((e) => e.filename), ...childFolders(folders, p).map(folderName)]);

  const addFiles = (picked) => {
    if (!picked.length) return;
    const tooBig = picked.find((file) => maxBytes && file.size > maxBytes);
    if (tooBig) return setError(`The file ${tooBig.name} is too large. The maximum size you can upload is ${formatLimit(maxBytes)}.`);
    if (entries.length + picked.length > maxFiles) return setError(`You can not attach more than ${maxFiles} file(s).`);
    const taken = namesIn(path);
    const added = picked.map((file) => {
      const filename = uniqueName(file.name, taken);
      taken.add(filename);
      return { key: nextKey(), filepath: path, filename, filesize: file.size, timemodified: Math.floor(Date.now() / 1000), file };
    });
    setError(null);
    onChange({ entries: [...entries, ...added], folders });
  };

  const createFolder = () => {
    const name = newName.trim().replace(/[/\\]/g, '');
    setCreating(false);
    setNewName('');
    if (!name) return;
    onChange({ entries, folders: [...folders, `${path}${uniqueName(name, namesIn(path))}/`] });
  };

  const remove = (item) => {
    if (item.folder) {
      onChange({ entries: entries.filter((e) => !e.filepath.startsWith(item.folder)), folders: folders.filter((f) => !f.startsWith(item.folder)) });
    } else {
      onChange({ entries: entries.filter((e) => e.key !== item.key), folders });
    }
    setEditing(null);
  };
  const rename = (item, name) => {
    const clean = name.trim().replace(/[/\\]/g, '');
    setEditing(null);
    if (item.folder) {
      const current = folderName(item.folder);
      if (!clean || clean === current) return;
      const parent = item.folder.slice(0, -current.length - 1);
      const target = `${parent}${uniqueName(clean, namesIn(parent))}/`;
      const move = (p) => (p.startsWith(item.folder) ? target + p.slice(item.folder.length) : p);
      onChange({ entries: entries.map((e) => ({ ...e, filepath: move(e.filepath) })), folders: folders.map(move) });
    } else {
      if (!clean || clean === item.filename) return;
      const filename = uniqueName(clean, namesIn(item.filepath));
      onChange({ entries: entries.map((e) => (e.key === item.key ? { ...e, filename } : e)), folders });
    }
  };

  const subfolders = childFolders(folders, path);
  const files = filesIn(path);
  const empty = !subfolders.length && !files.length;
  const crumbs = path.split('/').filter(Boolean);

  // Folder dibuka; di tampilan pohon (edit = true) folder dan file membuka dialog ubah nama/hapus.
  const openItem = (item, edit = false) => (item.folder && !edit ? setPath(item.folder) : setEditing({ ...item, name: item.filename }));
  const items = [...subfolders.map((folder) => ({ folder, filename: folderName(folder) })), ...files];

  return (
    <div>
      <div role="group" aria-labelledby={labelId} className="rounded-md border border-line bg-white">
        <div className="flex items-center justify-between gap-2 px-2 py-1.5">
          <div className="flex gap-1">
            <button type="button" title="Add..." aria-label="Add..." className={TOOL_BUTTON} onClick={() => inputRef.current?.click()}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M6 3h8l4 4v14H6zM14 3v4h4" /></svg>
            </button>
            <button type="button" title="Create folder" aria-label="Create folder" className={TOOL_BUTTON} onClick={() => setCreating(true)}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M3 6h6l2 2h10v11H3z" /></svg>
            </button>
          </div>
          <div className="flex overflow-hidden rounded" role="radiogroup" aria-label="Tampilan file">
            {VIEWS.map(([key, label, d]) => (
              <button
                key={key}
                type="button"
                role="radio"
                aria-checked={view === key}
                title={label}
                aria-label={label}
                className={`grid h-7 w-8 cursor-pointer place-items-center ${view === key ? 'bg-[#ced4da]' : 'bg-line-subtle hover:bg-line'}`}
                onClick={() => setView(key)}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill={key === 'details' ? 'none' : 'currentColor'} stroke={key === 'details' ? 'currentColor' : 'none'} strokeWidth="2.5" aria-hidden="true"><path d={d} /></svg>
              </button>
            ))}
          </div>
        </div>
        <nav aria-label="Jalur folder" className="flex flex-wrap items-center gap-1 border-b border-line px-3 pb-1.5 text-sm">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 5h7l2 2h9v12H3z" /></svg>
          <button type="button" className="cursor-pointer text-primary hover:underline" onClick={() => setPath('/')}>Files</button>
          {crumbs.map((name, index) => {
            const to = `/${crumbs.slice(0, index + 1).join('/')}/`;
            return (
              <span key={to} className="flex items-center gap-1">
                <span aria-hidden="true" className="text-muted">▸</span>
                <button type="button" className="cursor-pointer text-primary hover:underline" onClick={() => setPath(to)}>{name}</button>
              </span>
            );
          })}
        </nav>
        <div
          className={`m-2 min-h-32 rounded ${dragging ? 'border-2 border-dashed border-primary bg-primary-light' : empty ? 'border-2 border-dashed border-[#8f959e]' : 'border-2 border-transparent'}`}
          onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => { event.preventDefault(); setDragging(false); addFiles([...event.dataTransfer.files]); }}
        >
          {empty ? (
            <div className="flex flex-col items-center gap-3 px-4 py-6 text-center text-sm text-ink-subtle">
              <svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="#6a737b" strokeWidth="2.5" aria-hidden="true">
                <circle cx="20" cy="20" r="17" />
                <path d="M20 10v18m-7-7 7 7 7-7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              You can drag and drop files here to add them.
            </div>
          ) : view === 'icons' ? (
            <ul className="flex flex-wrap gap-2 p-2" aria-label="Isi folder">
              {items.map((item) => (
                <li key={item.folder ?? item.key}>
                  <button type="button" className="flex w-28 cursor-pointer flex-col items-center gap-1 rounded p-2 text-center text-xs hover:bg-line-subtle" onClick={() => openItem(item)}>
                    {item.folder ? <FolderIcon /> : <FileIcon name={item.filename} />}
                    <span className="w-full wrap-anywhere">{item.filename}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : view === 'details' ? (
            <div className="table-wrap">
              <table className="table text-sm">
                <thead><tr><th>Name</th><th>Last modified</th><th>Size</th><th>Type</th></tr></thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.folder ?? item.key}>
                      <td>
                        <button type="button" className="flex cursor-pointer items-center gap-1.5 text-left hover:underline" onClick={() => openItem(item)}>
                          {item.folder ? <FolderIcon size={20} /> : <FileIcon name={item.filename} size={20} />}
                          <span className="wrap-anywhere">{item.filename}</span>
                        </button>
                      </td>
                      <td>{item.folder ? '' : formatUnixDateTime(item.timemodified)}</td>
                      <td>{item.folder ? '' : formatFileSize(item.filesize)}</td>
                      <td>{item.folder ? 'Folder' : (item.filename.split('.').pop() ?? '').toUpperCase()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-2 text-sm"><Tree at="/" folders={folders} entries={entries} onOpen={openItem} /></div>
          )}
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple={maxFiles > 1}
          className="sr-only"
          tabIndex={-1}
          aria-label="Pilih file pengumpulan"
          onChange={(event) => { addFiles([...event.target.files]); event.target.value = ''; }}
        />
      </div>
      {error && <p role="alert" className="mt-1 text-sm font-semibold text-danger">{error}</p>}

      <Modal open={creating} title="Create folder" onClose={() => setCreating(false)}
        footer={<>
          <button type="button" className="btn" onClick={() => setCreating(false)}>Cancel</button>
          <button type="button" className="btn btn--primary" onClick={createFolder}>Create folder</button>
        </>}
      >
        <label className="flex flex-col gap-1.5 text-sm font-semibold">
          New folder name
          <input value={newName} autoFocus onChange={(event) => setNewName(event.target.value)}
            onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); createFolder(); } }} />
        </label>
      </Modal>
      <Modal open={!!editing} title={editing ? `Edit ${editing.folder ? folderName(editing.folder) : editing.filename}` : ''} onClose={() => setEditing(null)}
        footer={editing && <>
          {editing.fileurl && <a className="btn mr-auto" href={withToken(editing.fileurl)} target="_blank" rel="noreferrer">Download</a>}
          <button type="button" className="btn btn--danger" onClick={() => remove(editing)}>Delete</button>
          <button type="button" className="btn" onClick={() => setEditing(null)}>Cancel</button>
          <button type="button" className="btn btn--primary" onClick={() => rename(editing, editing.name)}>Update</button>
        </>}
      >
        {editing && (
          <div className="form">
            <label className="flex flex-col gap-1.5 text-sm font-semibold">
              Name
              <input value={editing.name} onChange={(event) => setEditing({ ...editing, name: event.target.value })} />
            </label>
            {!editing.folder && (
              <dl className="grid grid-cols-[120px_1fr] gap-1 text-sm">
                <dt className="text-muted">Path</dt><dd>{editing.filepath}</dd>
                <dt className="text-muted">Size</dt><dd>{formatFileSize(editing.filesize)}</dd>
              </dl>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
