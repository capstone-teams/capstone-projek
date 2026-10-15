import { Navigate, Route, Routes } from 'react-router-dom';
<<<<<<< HEAD
import MoodleLayout from './components/layout/MoodleLayout';
import RequireAuth from './components/layout/RequireAuth';
import ForgotPasswordPage from './pages/auth/ForgotPasswordPage';
import LoginPage from './pages/auth/LoginPage';
=======
import MoodleLayout from './components/MoodleLayout';
import RequireAuth from './components/RequireAuth';
<<<<<<< HEAD
=======
import ForgotPasswordPage from './pages/ForgotPasswordPage';
>>>>>>> origin/develop
import LoginPage from './pages/LoginPage';
>>>>>>> 8a5a3ec2c6308f208b58dd368f4aa3cdb9316534
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
// Generator Konten AI (tab di halaman kursus, khusus dosen pengampu)
import AiCourseLayout from './pages/ai/course/AiCourseLayout';
import CourseOverviewPage from './pages/ai/course/CourseOverviewPage';
import CourseRpsPage from './pages/ai/course/CourseRpsPage';
import CoursePlanPage from './pages/ai/course/CoursePlanPage';
import CourseContentPage from './pages/ai/course/CourseContentPage';
import CourseReviewPage from './pages/ai/course/CourseReviewPage';
import CoursePublishPage from './pages/ai/course/CoursePublishPage';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
<<<<<<< HEAD
=======
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
>>>>>>> origin/develop

      <Route element={<RequireAuth />}>
        <Route element={<MoodleLayout />}>
          <Route index element={<Navigate to="/my" replace />} />
          <Route path="my" element={<DashboardPage />} />
          <Route path="my/courses" element={<MyCoursesPage />} />
          <Route path="user/profile" element={<ProfilePage />} />

          <Route path="course/:courseId" element={<MoodleCourseLayout />}>
            <Route index element={<CourseViewPage />} />
            <Route path="participants" element={<ParticipantsPage />} />
            <Route path="grades" element={<GradesPage />} />
            <Route path="mod/:cmid" element={<ActivityPage />} />
            <Route element={<RequireAuth roles={['dosen']} />}>
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
