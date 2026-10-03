# Frontend service boundary

Feature pages call `courseService` from `services/index.ts`. They do not import
`data/courseData.ts` directly. `mockCourseService.ts` supplies development data
without a backend, and `useServiceResource.ts` provides loading, error, and retry
states for asynchronous reads.

`CourseService` in `courseService.ts` is the UI-facing contract. When real Backend
endpoints and response schemas are finalized, add an HTTP implementation of this
interface using `createApiClient()` and change the binding in `index.ts`. The
pages can continue calling the same methods. Keep endpoint-specific mapping in
that implementation so API payloads do not become page props directly.

`apiClient.ts` uses `/api/v1` from `docs/02. design/design-api.md`, sends JSON,
and maps the documented `{ error: { code, message, details } }` envelope to
`ApiError`. It also distinguishes transport, cancellation, and malformed JSON
responses. Exact course-list and material endpoints are not specified in the
current API draft, so this foundation does not invent them or enable real API
calls yet.
