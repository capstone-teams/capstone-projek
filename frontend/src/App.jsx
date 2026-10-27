import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import { ROLE, homePathFor } from './types/auth';
import MoodleLayout from './components/layout/MoodleLayout';
import RequireAuth from './components/layout/RequireAuth';
import ForgotPasswordPage from './pages/auth/ForgotPasswordPage';
import LoginPage from './pages/auth/LoginPage';
import { NotFoundPage } from './pages/StatusPage';
// Moodle (dosen & mahasiswa)
import DashboardPage from './pages/moodle/DashboardPage';
import MyCoursesPage from './pages/moodle/MyCoursesPage';
import ProfilePage from './pages/moodle/ProfilePage';
import MoodleCourseLayout from './pages/moodle/course/MoodleCourseLayout';
import CourseViewPage from './pages/moodle/course/CourseViewPage';
import ParticipantsPage from './pages/moodle/course/ParticipantsPage';
import GradesPage from './pages/moodle/course/GradesPage';
import ActivityPage from './pages/moodle/course/ActivityPage';
import EditSubmissionPage from './pages/moodle/course/EditSubmissionPage';
import ModEditPage from './pages/moodle/course/ModEditPage';
// Generator Konten AI (tab di halaman kursus, khusus dosen pengampu)
import AiCourseLayout from './pages/ai/course/AiCourseLayout';
import CourseOverviewPage from './pages/ai/course/CourseOverviewPage';
import CourseRpsPage from './pages/ai/course/CourseRpsPage';
import CoursePlanPage from './pages/ai/course/CoursePlanPage';
import CourseContentPage from './pages/ai/course/CourseContentPage';
import CourseReviewPage from './pages/ai/course/CourseReviewPage';
import CoursePublishPage from './pages/ai/course/CoursePublishPage';

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

          <Route path="course/:courseId" element={<MoodleCourseLayout />}>
            <Route index element={<CourseViewPage />} />
            <Route path="participants" element={<ParticipantsPage />} />
            <Route path="grades" element={<GradesPage />} />
            <Route path="mod/:cmid" element={<ActivityPage />} />
            <Route path="mod/:cmid/editsubmission" element={<EditSubmissionPage />} />
            <Route path="modedit" element={<ModEditPage />} />
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
