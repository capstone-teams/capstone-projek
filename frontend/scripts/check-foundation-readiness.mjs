import { readFileSync } from 'node:fs'

const report = JSON.parse(readFileSync(new URL('../.cache/playwright/results.json', import.meta.url), 'utf8'))
const tests = []
function collect(suite) {
  for (const spec of suite.specs ?? []) {
    for (const test of spec.tests) tests.push({ title: spec.title, ...test })
  }
  for (const child of suite.suites ?? []) collect(child)
}
for (const suite of report.suites) collect(suite)

const blockers = tests.filter((test) => test.expectedStatus === 'failed')
const incomplete = tests.filter((test) => test.expectedStatus !== 'failed'
  && (test.expectedStatus !== 'passed' || test.status !== 'expected'))
const passed = tests.filter((test) => test.expectedStatus === 'passed' && test.status === 'expected')

console.log(`Foundation: ${passed.length} browser checks passed, ${blockers.length} known blockers, ${incomplete.length} other incomplete checks.`)
for (const test of blockers) {
  console.log(`BLOCKED: ${test.title} — ${test.annotations.find((annotation) => annotation.type === 'fail')?.description ?? 'Pending dependency.'}`)
}
for (const test of incomplete) console.log(`INCOMPLETE: ${test.title} (${test.status})`)

// Expected failures count as passing in Playwright but block frontend readiness.
if (tests.length === 0 || blockers.length > 0 || incomplete.length > 0 || report.errors?.length > 0) {
  console.error('Frontend verification is incomplete. Resolve the reported checks and rerun verification.')
  process.exitCode = 1
}
