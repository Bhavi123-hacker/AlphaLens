# P18 dependency and license review

The mandatory frontend runs locally using free/open-source software. All direct
dependencies are pinned in `apps/web/package.json`, with exact transitive versions
and registry integrity hashes in `package-lock.json`. The existing Python lock is
unchanged. Node 22 LTS is a local tool, not a paid service or required cloud account.

| Package group | License | Purpose |
| --- | --- | --- |
| React / React DOM / React Router | MIT | Accessible component rendering and local routes |
| TanStack Query | MIT | Persisted-read caching, cancellation and deduplication |
| Apache ECharts | Apache-2.0 | Candlesticks, volume, stored indicators and metric visualizations |
| Lucide React | ISC | Interface icons |
| Zod | MIT | Runtime validation of actual API envelopes/domain records |
| Inter / JetBrains Mono fonts | OFL-1.1 | Self-hosted typography; no external font requests |
| Vite / Tailwind / ESLint / TypeScript ESLint / Vitest | MIT | Local build, styling and verification |
| TypeScript | Apache-2.0 | Static contracts |
| OpenAPI TypeScript | MIT | Offline generation from P17's committed schema |
| Playwright | Apache-2.0 | Actual local Chromium browser verification |
| axe-core tooling | MPL-2.0 | Automated accessibility inspection; no source modifications |
| Testing Library / jsdom / type declarations | MIT | Isolated TEST_ONLY unit/component tests |

Runtime license texts and applicable NOTICE files are preserved in
`apps/web/public/third-party-notices.txt`, generated from the frozen installed
packages by `scripts/generate-notices.mjs`. The Settings page links to this
same-origin text. Fonts are bundled under their original names without modification.
No paid UI kit, chart subscription, model API, auth service or market-data provider
is added.

Primary publisher license references:
[ECharts Apache license](https://github.com/apache/echarts/blob/master/LICENSE),
[Vite MIT license](https://github.com/vitejs/vite/blob/main/packages/vite/LICENSE.md),
[TanStack Query package/license metadata](https://github.com/TanStack/query/blob/main/packages/react-query/package.json).
Registry metadata and installed license files were also reviewed before release.
The npm audit result is recorded in the separate P18 verification report; it does
not waive the existing backend image's 44 HIGH OS findings or strict Trivy gate.
