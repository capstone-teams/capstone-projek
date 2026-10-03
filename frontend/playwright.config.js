import { defineConfig } from '@playwright/test';
export default defineConfig({
    testDir: './tests/e2e',
    testMatch: ['**/rakha-runtime.spec.js', '**/foundation-71.spec.js', '**/course-plan-74.spec.js'],
    forbidOnly: Boolean(process.env.CI),
    workers: 1,
    retries: 0,
    outputDir: '.cache/playwright/results',
    reporter: [
        ['list'],
        ['html', { outputFolder: '.cache/playwright/report', open: 'never' }],
        ['json', { outputFile: '.cache/playwright/results.json' }],
    ],
    use: {
        browserName: 'chromium',
        channel: process.env.PLAYWRIGHT_CHANNEL || (process.platform === 'win32' ? 'chrome' : undefined),
        baseURL: 'http://127.0.0.1:4173',
        viewport: { width: 1440, height: 900 },
        trace: 'retain-on-failure',
        screenshot: 'only-on-failure',
    },
    webServer: {
        env: { VITE_MOODLE_MOCK: 'true', VITE_USE_MOCK: 'true' },
        command: 'npm run dev -- --host 127.0.0.1 --port 4173 --configLoader runner',
        url: 'http://127.0.0.1:4173',
        reuseExistingServer: false,
        timeout: 30_000,
    },
});
