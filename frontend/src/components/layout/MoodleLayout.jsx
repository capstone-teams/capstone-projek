import { Outlet } from 'react-router-dom';
import AppStatus from './AppStatus';
import ApplicationHeader from './ApplicationHeader';

export default function MoodleLayout() {
  return <div className="approved-app"><ApplicationHeader /><AppStatus /><Outlet /></div>;
}

export function PageContainer({ children }) {
  return <main className="approved-page">{children}</main>;
}
