import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import { ROLE, homePathFor } from './types/auth';
import MoodleLayout from './components/layout/MoodleLayout';
import RequireAuth from './components/layout/RequireAuth';
import ForgotPasswordPage from './pages/auth/ForgotPasswordPage';
import LoginPage from './pages/auth/LoginPage';
import { ForbiddenPage, NotFoundPage } from './pages/StatusPage';
import ByCourseRole from './components/layout/ByCourseRole';
// Bersama (dosen & mahasiswa)
import MyCoursesPage from './pages/moodle/MyCoursesPage';
import ProfilePage from './pages/moodle/ProfilePage';
import MoodleCourseLayout from './pages/moodle/course/MoodleCourseLayout';
// Dosen
import DashboardPage from './pages/dosen/DashboardPage';
import DosenCourseViewPage from './pages/dosen/course/CourseViewPage';
import DosenParticipantsPage from './pages/dosen/course/ParticipantsPage';
import DosenGradesPage from './pages/dosen/course/GradesPage';
import DosenActivityPage from './pages/dosen/course/ActivityPage';
import ModEditPage from './pages/dosen/course/ModEditPage';
// Dosen: Generator Konten AI (tab di halaman kursus, khusus dosen pengampu)
import AiCourseLayout from './pages/dosen/ai/AiCourseLayout';
import CourseOverviewPage from './pages/dosen/ai/CourseOverviewPage';
import CourseRpsPage from './pages/dosen/ai/CourseRpsPage';
import CoursePlanPage from './pages/dosen/ai/CoursePlanPage';
import CourseContentPage from './pages/dosen/ai/CourseContentPage';
import CourseReviewPage from './pages/dosen/ai/CourseReviewPage';
import CoursePublishPage from './pages/dosen/ai/CoursePublishPage';
// Mahasiswa
import MahasiswaCourseViewPage from './pages/mahasiswa/course/CourseViewPage';
import MahasiswaParticipantsPage from './pages/mahasiswa/course/ParticipantsPage';
import MahasiswaGradesPage from './pages/mahasiswa/course/GradesPage';
import MahasiswaActivityPage from './pages/mahasiswa/course/ActivityPage';
import EditSubmissionPage from './pages/mahasiswa/course/EditSubmissionPage';

/** "/" membuka halaman awal sesuai role: dosen ke dashboard, mahasiswa ke halaman course. */
function HomeRedirect() {
  const { user } = useAuth();
  return <Navigate to={homePathFor(user?.role)} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />

      <Route element={<RequireAuth />}>
        <Route element={<MoodleLayout />}>
          <Route index element={<HomeRedirect />} />
          {/* Halaman dosen Sprint 1: dashboard (FE-11.1). Instructor Setup ada di Profil (khusus DOSEN). */}
          <Route element={<RequireAuth roles={[ROLE.DOSEN]} />}>
            <Route path="my" element={<DashboardPage />} />
          </Route>
          <Route path="my/courses" element={<MyCoursesPage />} />
          <Route path="user/profile" element={<ProfilePage />} />

          {/* URL kursus sama untuk semua; ByCourseRole memilih halaman dosen (pengajar kursus) atau mahasiswa. */}
          <Route path="course/:courseId" element={<MoodleCourseLayout />}>
            <Route index element={<ByCourseRole dosen={<DosenCourseViewPage />} mahasiswa={<MahasiswaCourseViewPage />} />} />
            <Route path="participants" element={<ByCourseRole dosen={<DosenParticipantsPage />} mahasiswa={<MahasiswaParticipantsPage />} />} />
            <Route path="grades" element={<ByCourseRole dosen={<DosenGradesPage />} mahasiswa={<MahasiswaGradesPage />} />} />
            <Route path="mod/:cmid" element={<ByCourseRole dosen={<DosenActivityPage />} mahasiswa={<MahasiswaActivityPage />} />} />
            <Route path="mod/:cmid/editsubmission" element={<ByCourseRole dosen={<ForbiddenPage />} mahasiswa={<EditSubmissionPage />} />} />
            <Route path="modedit" element={<ByCourseRole dosen={<ModEditPage />} mahasiswa={<ForbiddenPage />} />} />
            {/* RPS, Course Target, dan Monitoring berada di tab Generator AI (khusus DOSEN). */}
            <Route element={<RequireAuth roles={[ROLE.DOSEN]} />}>
              <Route path="ai" element={<AiCourseLayout />}>
                <Route index element={<CourseOverviewPage />} />
                <Route path="rps" element={<CourseRpsPage />} />
                <Route path="plan" element={<CoursePlanPage />} />
                <Route path="content" element={<CourseContentPage />} />
                <Route path="review" element={<CourseReviewPage />} />
                <Route path="publish" element={<CoursePublishPage />} />
              </Route>
            </Route>
          </Route>

          {/* Generator AI dulu menu tersendiri; sekarang dibuka dari tab kursus. */}
          <Route path="ai/*" element={<Navigate to="/my/courses" replace />} />

          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
