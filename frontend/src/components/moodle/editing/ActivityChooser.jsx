import { useState } from 'react';
import { usePreference } from '../../../hooks/useAppState';

const TABS = [
  { key: 'starred', label: 'Starred' },
  { key: 'all', label: 'All' },
  { key: 'activities', label: 'Activities' },
  { key: 'resources', label: 'Resources' },
  { key: 'recommended', label: 'Recommended' },
];

const SHOW = {
  starred: (type, starred) => starred.includes(type.modname),
  all: () => true,
  activities: (type) => type.kind === 'activity',
  resources: (type) => type.kind === 'resource',
  recommended: (type) => type.recommended,
};

function TileIcon({ type }) {
  return (
    <span className={`grid size-10 place-items-center rounded-lg ${type.iconClass}`} aria-hidden="true">
      <img src={`/moodle/mod/${type.modname}.svg`} alt="" className="size-6 brightness-0 invert" />
    </span>
  );
}

function Star({ filled }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill={filled ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinejoin="round">
      <path d="M12 2.5l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.4 6.1 20.5l1.2-6.5L2.5 9.4l6.6-.9z" />
    </svg>
  );
}

function InfoIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor">
      <path d="M12 2a10 10 0 100 20 10 10 0 000-20zm1 15h-2v-6h2zm0-8h-2V7h2z" />
    </svg>
  );
}

/**
 * Pemilih jenis aktivitas seperti "Add an activity or resource" di Moodle: pencarian, tab, dan
 * kartu dengan bintang serta info. Bintang disimpan per pengguna.
 * types: [{ modname, name, kind, recommended, description, iconClass }].
 */
export default function ActivityChooser({ types, onChoose }) {
  const [stored, setStarred] = usePreference('activityChooser.starred', null);
  const starred = Array.isArray(stored) ? stored : types.map((type) => type.modname);
  const [tab, setTab] = useState('starred');
  const [query, setQuery] = useState('');
  const [info, setInfo] = useState(null);

  const search = query.trim().toLowerCase();
  const visible = types.filter((type) => (search ? type.name.toLowerCase().includes(search) : SHOW[tab](type, starred)));
  const toggleStar = (modname) => setStarred(starred.includes(modname) ? starred.filter((name) => name !== modname) : [...starred, modname]);

  if (info) {
    return (
      <div>
        <button type="button" className="btn btn--ghost btn--sm mb-3" onClick={() => setInfo(null)}>← Back</button>
        <div className="flex items-center gap-3">
          <TileIcon type={info} />
          <h3 className="text-lg">{info.name}</h3>
        </div>
        <p className="my-4">{info.description}</p>
        <button type="button" className="btn btn--primary" onClick={() => onChoose(info)}>Add</button>
      </div>
    );
  }

  return (
    <div>
      <input
        type="search"
        className="mb-4 rounded-full"
        placeholder="Search"
        aria-label="Search"
        autoFocus
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      {!search && (
        <div role="tablist" className="-mb-px flex flex-wrap gap-1 px-1" aria-label="Category">
          {TABS.map(({ key, label }) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={tab === key}
              className={`cursor-pointer rounded-t-md border px-3 py-1.5 text-sm ${tab === key ? 'border-line border-b-surface bg-surface text-ink' : 'border-transparent text-primary hover:underline'}`}
              onClick={() => setTab(key)}
            >
              {label}
            </button>
          ))}
        </div>
      )}
      <div role={search ? undefined : 'tabpanel'} className="min-h-[200px] rounded-md border border-line bg-surface p-3">
        {visible.length ? (
          <ul className="m-0 grid list-none grid-cols-[repeat(auto-fill,minmax(96px,1fr))] gap-3 p-0" aria-label="Activities and resources">
            {visible.map((type) => (
              <li key={type.modname} className="flex flex-col rounded-lg bg-white shadow-[0_1px_3px_rgba(0,0,0,0.12)]">
                <button
                  type="button"
                  className="flex flex-1 cursor-pointer flex-col items-center gap-2 rounded-t-lg px-2 pt-3 pb-1 text-center text-[13px] leading-tight text-ink hover:bg-primary-light focus-visible:outline-2 focus-visible:outline-primary"
                  onClick={() => onChoose(type)}
                >
                  <TileIcon type={type} />
                  <span>{type.name}</span>
                </button>
                <div className="flex items-center justify-center gap-4 pb-2 text-[#0f56b3]">
                  <button
                    type="button"
                    className="grid cursor-pointer place-items-center rounded-full p-0.5 focus-visible:outline-2 focus-visible:outline-primary"
                    aria-label={`${starred.includes(type.modname) ? 'Unstar' : 'Star'} ${type.name}`}
                    aria-pressed={starred.includes(type.modname)}
                    onClick={() => toggleStar(type.modname)}
                  >
                    <Star filled={starred.includes(type.modname)} />
                  </button>
                  <button
                    type="button"
                    className="grid cursor-pointer place-items-center rounded-full p-0.5 text-[#4b5563] focus-visible:outline-2 focus-visible:outline-primary"
                    aria-label={`${type.name} info`}
                    onClick={() => setInfo(type)}
                  >
                    <InfoIcon />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">{search ? `No results for "${query.trim()}".` : 'Nothing here yet.'}</p>
        )}
      </div>
    </div>
  );
}
