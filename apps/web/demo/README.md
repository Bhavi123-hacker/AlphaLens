# AlphaLens independent public-demo package

Entirely generated TEST_ONLY examples. No private API, credentials, accounts,
real NSE data, trained model artifacts or measured model results. Static entry
and Vite config are separate from the authenticated application. CSP connect-src
none; no API proxy or runtime provider configuration. Original P6 formulas are
applied to deterministic synthetic inputs by the Python generator, not the browser.

Build with `npm run build:demo` from apps/web after generating demo/data.json using
`python -m scripts.build_p29_public_demo --output apps/web/demo/data.json`.
The dataset is explicitly synthetic and original; no source-market rights apply.
See docs/operations/p29-public-demo.md for local preview, testing, licence notices
and a publication plan. Nothing is deployed or enabled automatically.
