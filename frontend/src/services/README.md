# Frontend service boundary

Feature pages call `courseService` from `services/index.js`. They do not import
`data/courseData.js` directly. `mockCourseService.js` retains approved UI fixtures.
`useServiceResource.js` adapts Rakha's shared `useApi` hook to the page-facing
loading/error/success/retry contract. Both hooks ignore obsolete responses.

The approved presentation contract is the set of methods on `mockCourseService`:
`listInstructorCourses`, `listStudentCourses`, `listSyllabusWeeks`, `getRpsAnalysis`,
`getMaterial`. Add a response adapter and change the binding in `index.js` when
connecting these pages to real data. Keep API payload mapping in that adapter.

`courseService.js`, `rpsService.js`, `profileService.js`, `monitoringSocket.js` and
`mock/` were brought from Rakha's `accbc21`. They expose backend API operations
and a separate backend workflow simulation. They are available to feature work;
the approved pages do not yet invoke these workflow operations. Their response
shapes and fixture catalog differ from the presentation fixtures.

`apiClient.js` uses `/api/v1` from `docs/02. design/design-api.md`, sends JSON,
and maps the documented `{ error: { code, message, details } }` envelope to
`ApiError`. It also distinguishes transport, cancellation, and malformed JSON
responses. The original FE-03.2 `createApiClient` HTTP engine is retained. Rakha's
`api.get/post/put` facade adds runtime mock selection, Bearer authentication,
query parameters, idempotency keys and session invalidation on 401.

Authentication is connected through `authService`: login sends `{ username,
password }`, followed by `/auth/me`. With the real backend, `username` contains
the user's email. Mock accounts accept the exact demo username or email and
validate the defined password; they never create a user from arbitrary input.
AuthProvider alone commits the token after a current login response, preventing
late responses from restoring a logged-out or replaced session.

`VITE_USE_MOCK=false` connects authentication and explicitly invoked backend
services to real HTTP. It does **not** replace the presentation mock adapter or
the local RPS/plan/content/publishing demo. Moodle is reached through backend
operations; the browser Moodle client from Rakha's UI was not imported. Real
WebSocket auth is still an open backend contract and is not exercised by this UI.
