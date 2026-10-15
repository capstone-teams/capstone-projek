import { execFileSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

// The approved implemented mockup, before FE-03.2. Never derive references from HEAD.
const baselineCommit = 'e9807a530771263dda11f460f59ed77653c6df71'
const repository = fileURLToPath(new URL('../../', import.meta.url))
const destination = fileURLToPath(new URL('../.cache/design-baseline/', import.meta.url))
const archive = fileURLToPath(new URL('../.cache/design-baseline/source.tar', import.meta.url))
mkdirSync(destination, { recursive: true })
execFileSync('git', ['archive', '--format=tar', `--output=${archive}`, baselineCommit, 'frontend'], { cwd: repository })
execFileSync('tar', ['-xf', archive, '-C', destination])
console.log(`Approved UI reference: ${baselineCommit}`)
