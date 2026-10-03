import { defineConfig } from '@playwright/test';
import foundation from './playwright.config';
export default defineConfig({
    ...foundation,
    testMatch: '**/design-conformance.spec.js',
    outputDir: '.cache/design-conformance/results',
    snapshotPathTemplate: '{testDir}/../../.cache/design-conformance/reference/{testFilePath}/{arg}{ext}',
    updateSnapshots: 'none',
    reporter: [
        ['list'],
        ['html', { outputFolder: '.cache/design-conformance/report', open: 'never' }],
        ['json', { outputFile: '.cache/design-conformance/results.json' }],
    ],
    use: { ...foundation.use, reducedMotion: 'reduce' },
    webServer: [
        ...(Array.isArray(foundation.webServer) ? foundation.webServer : [foundation.webServer]),
        {
            command: 'node scripts/prepare-design-baseline.mjs && node node_modules/vite/bin/vite.js .cache/design-baseline/frontend --config .cache/design-baseline/frontend/vite.config.ts --configLoader runner --host 127.0.0.1 --port 4174',
            url: 'http://127.0.0.1:4174',
            reuseExistingServer: false,
            timeout: 30_000,
        },
    ],
});
