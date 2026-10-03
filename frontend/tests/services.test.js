// @vitest-environment node
import { describe, test } from 'vitest';
import assert from 'node:assert/strict';
import { createApiClient } from '../src/services/apiClient.js';
import { ApiError } from '../src/services/apiError.js';
import { mockCourseService } from '../src/services/mockCourseService.js';
describe('course service boundary', () => {
    test('mock data is available without a backend and is not shared by reference', async () => {
        const courses = await mockCourseService.listInstructorCourses();
        assert.equal(courses.length, 3);
        assert.equal(courses[0].code, 'IF201405');
        courses[0].name = 'changed locally';
        assert.notEqual((await mockCourseService.listInstructorCourses())[0].name, 'changed locally');
        assert.equal((await mockCourseService.listStudentCourses()).length, 3);
        assert.equal((await mockCourseService.listSyllabusWeeks()).length, 16);
        assert.equal((await mockCourseService.getRpsAnalysis()).weeklyPlans.length, 16);
    });
    test('mock material lookup preserves the existing week fallback', async () => {
        assert.equal((await mockCourseService.getMaterial('missing', 2)).weekNumber, 2);
        assert.equal((await mockCourseService.getMaterial('missing', 3)).weekNumber, 3);
    });
});
describe('API client', () => {
    test('builds a versioned GET request and returns JSON', async () => {
        let requestedUrl = '';
        let accept = '';
        const client = createApiClient({
            fetchImpl: async (input, init) => {
                requestedUrl = String(input);
                accept = new Headers(init?.headers).get('Accept') ?? '';
                return new Response(JSON.stringify({ id: 'course-1' }), { status: 200 });
            },
        });
        assert.deepEqual(await client.get('/courses/course-1'), { id: 'course-1' });
        assert.equal(requestedUrl, '/api/v1/courses/course-1');
        assert.equal(accept, 'application/json');
    });
    test('sends JSON for POST requests and accepts empty success responses', async () => {
        let requestBody = '';
        let contentType = '';
        const client = createApiClient({
            fetchImpl: async (_input, init) => {
                requestBody = String(init?.body);
                contentType = new Headers(init?.headers).get('Content-Type') ?? '';
                return new Response(null, { status: 204 });
            },
        });
        assert.equal(await client.post('courses', { name: 'Aljabar Linear' }), undefined);
        assert.equal(requestBody, JSON.stringify({ name: 'Aljabar Linear' }));
        assert.equal(contentType, 'application/json');
    });
    test('maps the documented API error envelope', async () => {
        const client = createApiClient({
            fetchImpl: async () => new Response(JSON.stringify({
                error: { code: 'VALIDATION_FAILED', message: 'Input RPS tidak valid.', details: ['file'] },
            }), { status: 422 }),
        });
        await assert.rejects(client.get('rps/1'), (error) => {
            assert.ok(error instanceof ApiError);
            assert.equal(error.kind, 'validation');
            assert.equal(error.status, 422);
            assert.equal(error.code, 'VALIDATION_FAILED');
            assert.deepEqual(error.details, ['file']);
            return true;
        });
    });
    test('maps HTTP failures even when the response is not JSON', async () => {
        const client = createApiClient({
            fetchImpl: async () => new Response('Service unavailable', { status: 503 }),
        });
        await assert.rejects(client.get('courses/1'), (error) => {
            assert.ok(error instanceof ApiError);
            assert.equal(error.kind, 'server');
            assert.equal(error.status, 503);
            return true;
        });
    });
    test('separates transport, cancelled, and invalid JSON responses', async () => {
        const networkClient = createApiClient({ fetchImpl: async () => { throw new TypeError('offline'); } });
        await assert.rejects(networkClient.get('courses/1'), (error) => error instanceof ApiError && error.kind === 'network');
        const abortedClient = createApiClient({ fetchImpl: async () => {
                throw new DOMException('aborted', 'AbortError');
            } });
        await assert.rejects(abortedClient.get('courses/1'), (error) => error instanceof ApiError && error.kind === 'cancelled');
        const badJsonClient = createApiClient({
            fetchImpl: async () => new Response('not JSON', { status: 200 }),
        });
        await assert.rejects(badJsonClient.get('courses/1'), (error) => error instanceof ApiError && error.kind === 'invalid-response');
    });
});
