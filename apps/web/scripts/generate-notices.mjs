import { readFileSync, readdirSync, writeFileSync, mkdirSync } from 'node:fs'
import { join } from 'node:path'
const lock = JSON.parse(readFileSync('package-lock.json', 'utf8'))
const notices = ['AlphaLens frontend third-party notices', 'Generated from the frozen npm lockfile; market data is not distributed in this bundle.', '']
for (const [path, entry] of Object.entries(lock.packages).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0)) {
  if (!path || entry.dev || entry.devOptional) continue
  const name = path.split('node_modules/').at(-1)
  const licenses = readdirSync(path).filter((file) => /^(LICENSE|NOTICE|COPYING|OFL)(?:[.-].*)?$/i.test(file)).sort()
  if (!licenses.length) throw new Error(`No retained license text found for ${name}`)
  notices.push(`=== ${name}@${entry.version} · ${entry.license ?? 'see license text'} ===`, '')
  for (const file of licenses) notices.push(file, readFileSync(join(path, file), 'utf8').replaceAll('\r\n', '\n'), '')
}
mkdirSync('public', { recursive: true })
writeFileSync('public/third-party-notices.txt', notices.join('\n').trimEnd() + '\n')
console.log('Retained runtime licenses and notices from pinned installed packages.')
