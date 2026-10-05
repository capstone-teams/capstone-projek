import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { expect, test } from '@playwright/test';
import { openAs } from './session.js';
const baselineURL = 'http://127.0.0.1:4174';
const viewports = [
    { width: 375, height: 812 },
    { width: 768, height: 1024 },
    { width: 1440, height: 900 },
];
const screens = [
    ['/login', 'login'],
    ['/dashboard', 'dashboard-empty'],
    ['/dashboard?hasCourses=true', 'dashboard-courses'],
    ['/rps-analysis', 'rps-analysis'],
    ['/course-plan', 'plan-empty'],
    ['/course-plan?planStage=review', 'plan-review'],
    ['/course-plan?planStage=approved', 'plan-approved'],
    ['/course-plan?planStage=published', 'plan-published'],
    ['/weekly-content', 'content-empty'],
    ['/weekly-content?contentStage=review', 'content-review'],
    ['/weekly-content?contentStage=synced', 'content-synced'],
    ['/material-view', 'material-reader'],
    ['/student/courses', 'student-courses'],
    ['/student/course', 'student-course'],
    ['/student/week', 'student-week'],
];
async function settle(page) {
    await expect(page.locator('h1')).toBeVisible();
    await expect(page.getByRole('status')).toHaveCount(0);
    await page.evaluate(() => document.fonts.ready);
}
async function appearance(page) {
    return page.evaluate(() => {
        const properties = [
            'font-family', 'font-size', 'font-weight', 'line-height', 'color',
            'background-color', 'padding', 'margin', 'gap', 'border-radius',
            'border-color', 'box-shadow',
        ];
        return [...document.querySelectorAll('header, h1, h2, h3, button, input, select, [role="dialog"]')]
            .filter((element) => element.getBoundingClientRect().width > 0)
            .map((element) => {
            const style = getComputedStyle(element);
            const rect = element.getBoundingClientRect();
            return {
                tag: element.tagName,
                text: element.textContent,
                bounds: [rect.x, rect.y, rect.width, rect.height],
                style: Object.fromEntries(properties.map((property) => [property, style.getPropertyValue(property)])),
            };
        });
    });
}
// Reference screenshots come exclusively from the archived approved commit.
// Both versions run in the same browser/OS; no current-source snapshot approval.
for (const viewport of viewports) {
    test.describe(`${viewport.width}px approved design`, () => {
        test.use({ viewport });
        for (const [path, name] of screens) {
            test(name, async ({ page, context }, testInfo) => {
                const reference = await context.newPage();
                await reference.goto(`${baselineURL}${path}`);
                await openAs(page, path);
                await settle(reference);
                await settle(page);
                const snapshotName = `${name}-${viewport.width}.png`;
                const snapshotPath = testInfo.snapshotPath(snapshotName);
                mkdirSync(dirname(snapshotPath), { recursive: true });
                writeFileSync(snapshotPath, await reference.screenshot({ fullPage: true, animations: 'disabled' }));
                await testInfo.attach('approved-baseline', { path: snapshotPath, contentType: 'image/png' });
                await testInfo.attach('current', { body: await page.screenshot({ fullPage: true, animations: 'disabled' }), contentType: 'image/png' });
                if (name !== 'login') {
                    await expect(page).toHaveScreenshot(snapshotName, { fullPage: true, animations: 'disabled', maxDiffPixels: 0 });
                expect(await appearance(page)).toEqual(await appearance(reference));
                } else {
                    // Validated demo credentials change helper wrapping and vertical centering.
                    // Keep typography, colors, dimensions and horizontal placement identical.
                    const stable = (elements) => elements.map(({ bounds, ...element }) => ({
                        ...element, bounds: [bounds[0], bounds[2], bounds[3]],
                    }));
                    expect(stable(await appearance(page))).toEqual(stable(await appearance(reference)));
                    await expect(page.getByText('dosen / dosen123', { exact: true })).toBeVisible();
                    await expect(page.getByText('mahasiswa / mahasiswa123', { exact: true })).toBeVisible();
                }
                await reference.close();
            });
        }
        for (const modal of ['upload', 'profile', 'menu']) {
            test(`${modal} overlay`, async ({ page, context }, testInfo) => {
                const reference = await context.newPage();
                for (const target of [reference, page]) {
                    if (target === reference) await target.goto(`${baselineURL}/dashboard`);
                    else await openAs(target, '/dashboard');
                    await settle(target);
                    if (modal === 'upload') {
                        await target.getByRole('button', { name: '+ Upload RPS', exact: true }).click();
                    }
                    else {
                        await target.locator('button[aria-haspopup="menu"]').click();
                        if (modal === 'profile')
                            await target.getByRole('menuitem', { name: 'Profil Dosen', exact: true }).click();
                    }
                    await expect(target.getByRole(modal === 'menu' ? 'menu' : 'dialog')).toBeVisible();
                }
                const snapshotName = `${modal}-${viewport.width}.png`;
                const snapshotPath = testInfo.snapshotPath(snapshotName);
                mkdirSync(dirname(snapshotPath), { recursive: true });
                writeFileSync(snapshotPath, await reference.screenshot({ fullPage: true, animations: 'disabled' }));
                await testInfo.attach('approved-baseline', { path: snapshotPath, contentType: 'image/png' });
                await testInfo.attach('current', { body: await page.screenshot({ fullPage: true, animations: 'disabled' }), contentType: 'image/png' });
                if (modal !== 'menu') {
                    await expect(page).toHaveScreenshot(snapshotName, { fullPage: true, animations: 'disabled', maxDiffPixels: 0 });
                    expect(await appearance(page)).toEqual(await appearance(reference));
                } else {
                    await expect(page.getByRole('menuitem')).toHaveCount(2);
                    await expect(page.getByRole('menuitem', { name: 'Profil Dosen', exact: true })).toBeVisible();
                    await expect(page.getByRole('menuitem', { name: /Keluar/ })).toBeVisible();
                    await expect(page.getByRole('menu').getByText('Akun aktif', { exact: true })).toBeVisible();
                    expect(await page.locator('header').evaluate(el => el.getBoundingClientRect().height)).toEqual(await reference.locator('header').evaluate(el => el.getBoundingClientRect().height));
                }
                await reference.close();
            });
        }
    });
}
test('student navigation matches the approved demo flow', async ({ page, context }) => {
    const reference = await context.newPage();
    const flows = [];
    for (const target of [reference, page]) {
        const paths = [];
        if (target === reference) await target.goto(`${baselineURL}/student/courses`);
        else await openAs(target, '/student/courses');
        await settle(target);
        await target.getByRole('button', { name: /IF201405.*Aljabar Linear dan Geometri/ }).click();
        await expect(target).toHaveURL(/\/student\/course$/);
        paths.push(new URL(target.url()).pathname);
        await target.getByRole('button', { name: /Minggu 03.*Determinan/ }).press('Enter');
        await expect(target).toHaveURL(/\/student\/week$/);
        paths.push(new URL(target.url()).pathname);
        await target.getByRole('button', { name: 'Kembali ke Mata Kuliah', exact: true }).click();
        await expect(target).toHaveURL(/\/student\/course$/);
        await target.getByRole('button', { name: /Agentic LMS/ }).press('Enter');
        await expect(target).toHaveURL(/\/student\/courses$/);
        paths.push(new URL(target.url()).pathname);
        flows.push(paths);
    }
    expect(flows[1]).toEqual(flows[0]);
    await reference.close();
});
