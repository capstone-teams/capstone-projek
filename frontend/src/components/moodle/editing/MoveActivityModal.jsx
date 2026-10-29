import { useState } from 'react';
import { Field, Modal } from '../../ui';

const END = 'end';

/** Pilih section dan posisi tujuan aktivitas (pengganti drag-and-drop yang dapat diakses keyboard). */
export default function MoveActivityModal({ open, activity, sections, onClose, onMove }) {
  const current = sections.find((s) => s.modules.some((m) => m.id === activity.id));
  const [sectionId, setSectionId] = useState(current?.id);
  const [position, setPosition] = useState(END);
  const [pending, setPending] = useState(false);

  const target = sections.find((s) => s.id === Number(sectionId)) ?? current;
  const others = target?.modules.filter((m) => m.id !== activity.id) ?? [];

  const submit = async (event) => {
    event.preventDefault();
    setPending(true);
    const ok = await onMove(target.id, position === END ? undefined : Number(position));
    setPending(false);
    if (ok) onClose();
  };

  return (
    <Modal open={open} title={`Pindahkan "${activity.name}"`} onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <Field label="Section tujuan">
          <select value={sectionId} onChange={(event) => { setSectionId(event.target.value); setPosition(END); }}>
            {sections.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </Field>
        <Field label="Posisi">
          <select value={position} onChange={(event) => setPosition(event.target.value)}>
            <option value={END}>Di akhir section</option>
            {others.map((m) => <option key={m.id} value={m.id}>Sebelum: {m.name}</option>)}
          </select>
        </Field>
        <div className="form__actions">
          <button type="button" className="btn btn--ghost" onClick={onClose}>Batal</button>
          <button type="submit" className="btn btn--primary" disabled={pending}>{pending ? 'Memindahkan…' : 'Pindahkan'}</button>
        </div>
      </form>
    </Modal>
  );
}
