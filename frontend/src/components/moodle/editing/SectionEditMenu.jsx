import ActionMenu from './ActionMenu';
import { DIRECT_EDITING_UNAVAILABLE, DIRECT_MOODLE_EDITING } from '../../../services/moodle/courseEditing';

/** Menu ⋮ section di Edit mode. Rujukan Moodle: section umum (nomor 0) tidak dapat disembunyikan. */
export default function SectionEditMenu({ section, editing }) {
  const hidden = section.visible === 0;
  const items = [
    section.section > 0 && (hidden
      ? { key: 'show', label: 'Tampilkan section', onSelect: () => editing.setSectionVisible(section, true) }
      : { key: 'hide', label: 'Sembunyikan section', onSelect: () => editing.setSectionVisible(section, false) }),
  ].filter(Boolean).map((item) => (DIRECT_MOODLE_EDITING ? item : { ...item, disabled: true, title: DIRECT_EDITING_UNAVAILABLE }));

  return <ActionMenu label={`Aksi untuk section ${section.name}`} items={items} disabled={editing.pending === `section:${section.id}`} />;
}
