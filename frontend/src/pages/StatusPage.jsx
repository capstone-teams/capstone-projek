import { Link } from 'react-router-dom';

function StatusLayout({ code, title, children }) {
  return (
    <div className="grid min-h-[60vh] place-items-center px-4 py-10">
      <div className="flex max-w-md flex-col items-center gap-3 text-center">
        <span className="text-6xl font-extrabold text-primary">{code}</span>
        <h1 className="text-2xl">{title}</h1>
        {children}
      </div>
    </div>
  );
}

export function NotFoundPage() {
  return (
    <StatusLayout code="404" title="Halaman tidak ditemukan">
      <Link to="/my" className="btn btn--primary">
        Ke Dasbor
      </Link>
    </StatusLayout>
  );
}

export function ForbiddenPage() {
  return (
    <StatusLayout code="403" title="Khusus dosen">
      <p className="text-muted">Halaman ini hanya untuk akun yang mengajar di Moodle. Mahasiswa dapat mengakses kursus dari Dasbor.</p>
      <Link to="/my" className="btn btn--primary">
        Ke Dasbor
      </Link>
    </StatusLayout>
  );
}
