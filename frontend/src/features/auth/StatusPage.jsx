// import { useAuth } from '../../hooks/useAuth';
// import { getDefaultPathForRole } from '../../utils/navigation';
// import { Link } from 'react-router-dom';
// import { Card } from '../../components/ui/Card';
// export function StatusPage({ forbidden = false }) {
//   const { user } = useAuth();
//   return <Card padding="lg">
//     <h1>{forbidden ? 'Akses tidak diizinkan' : 'Halaman tidak ditemukan'}</h1>
//     <p>{forbidden ? 'Halaman ini tidak tersedia untuk role akun Anda.' : 'Periksa alamat halaman yang ingin dibuka.'}</p>
//     <Link to={getDefaultPathForRole(user?.role)}>Kembali ke halaman utama</Link>
//   </Card>;
// }
