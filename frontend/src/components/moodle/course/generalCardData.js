// Kartu standar bagian atas kursus LMS ITK. Backend belum menyediakan forum pengumuman, presensi, maupun folder
// unggahan surat, jadi kartu tampil tanpa tautan dengan keterangan belum tersedia.
export const ANNOUNCEMENT_CARD = { key: 'pengumuman', modname: 'forum', name: 'Pengumuman' };
export const GENERAL_CARDS = [
  { key: 'presensi', modname: 'attendance', name: 'Presensi' },
  {
    key: 'surat',
    modname: 'folder',
    name: 'Surat Sakit dan Surat Izin',
    description:
      '<p>Silahkan mengupload surat sakit dan surat izin pada folder ini <strong>pada hari ketidakhadiran</strong>.</p>'
      + '<p>Format file: pdf</p><p>Format penamaan file: suratsakit/suratizin_NIM</p>',
  },
];
