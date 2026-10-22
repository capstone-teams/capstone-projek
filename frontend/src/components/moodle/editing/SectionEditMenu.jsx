import ActionMenu from './ActionMenu';
import { moodleEditUrl } from '../../../services/moodle/courseEditing';

/** Menu ⋮ section di Edit mode. Section umum (nomor 0) tidak dapat disembunyikan, seperti di Moodle. */
export default function SectionEditMenu({ section, editing }) {
  const hidden = section.visible === 0;
  const items = [
    { key: 'settings', label: 'Edit pengaturan', href: moodleEditUrl.sectionSettings(section.id) },
    section.section > 0 && (hidden
      ? { key: 'show', label: 'Tampilkan section', onSelect: () => editing.setSectionVisible(section, true) }
      : { key: 'hide', label: 'Sembunyikan section', onSelect: () => editing.setSectionVisible(section, false) }),
  ].filter(Boolean);

  return <ActionMenu label={`Aksi untuk section ${section.name}`} items={items} disabled={editing.pending === `section:${section.id}`} />;
}
