import { useState } from 'react';
import ActionMenu from './ActionMenu';
import DeleteActivityModal from './DeleteActivityModal';
import MoveActivityModal from './MoveActivityModal';
import { CM_ACTION, moodleEditUrl } from '../../../services/moodle/courseEditing';

/** Menu ⋮ aktivitas di Edit mode: pengaturan, pindah, indentasi, visibilitas, duplikat, peran, hapus. */
export default function ActivityEditMenu({ activity, sections, editing }) {
  const [dialog, setDialog] = useState(null);
  const busy = editing.pending?.endsWith(`:${activity.id}`);
  const hidden = !activity.visible;

  const items = [
    { key: 'settings', label: 'Edit pengaturan', href: moodleEditUrl.activitySettings(activity.id) },
    { key: 'move', label: 'Pindahkan', onSelect: () => setDialog('move') },
    { key: 'indent', label: 'Geser ke kanan', onSelect: () => editing.cmAction(activity, CM_ACTION.INDENT) },
    activity.indent > 0 && { key: 'outdent', label: 'Geser ke kiri', onSelect: () => editing.cmAction(activity, CM_ACTION.OUTDENT) },
    hidden
      ? { key: 'show', label: 'Tampilkan', onSelect: () => editing.cmAction(activity, CM_ACTION.SHOW) }
      : { key: 'hide', label: 'Sembunyikan', onSelect: () => editing.cmAction(activity, CM_ACTION.HIDE) },
    { key: 'duplicate', label: 'Duplikat', onSelect: () => editing.cmAction(activity, CM_ACTION.DUPLICATE) },
    activity.contextid && { key: 'roles', label: 'Atur peran', href: moodleEditUrl.assignRoles(activity.contextid) },
    { key: 'delete', label: 'Hapus', danger: true, onSelect: () => setDialog('delete') },
  ].filter(Boolean);

  return (
    <>
      <ActionMenu label={`Aksi untuk ${activity.name}`} items={items} disabled={busy} />
      {dialog === 'move' && (
        <MoveActivityModal
          open
          activity={activity}
          sections={sections}
          onClose={() => setDialog(null)}
          onMove={(sectionId, beforeCmId) => editing.moveCm(activity, sectionId, beforeCmId)}
        />
      )}
      {dialog === 'delete' && (
        <DeleteActivityModal
          open
          activity={activity}
          onClose={() => setDialog(null)}
          onConfirm={() => editing.cmAction(activity, CM_ACTION.DELETE)}
        />
      )}
    </>
  );
}
