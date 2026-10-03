import { defineConfig } from '@playwright/test';
import foundation from './playwright.config';
export default defineConfig({
    ...foundation,
    testMatch: '**/rakha-presentation.spec.js',
    outputDir: '.cache/design-conformance/results',
    snapshotPathTemplate: '{testDir}/../../.cache/design-conformance/reference/{testFilePath}/{arg}{ext}',
    updateSnapshots: 'none',
    reporter: [
        ['list'],
        ['html', { outputFolder: '.cache/design-conformance/report', open: 'never' }],
        ['json', { outputFile: '.cache/design-conformance/results.json' }],
    ],
    use: { ...foundation.use, reducedMotion: 'reduce' },
    webServer: foundation.webServer,
});
