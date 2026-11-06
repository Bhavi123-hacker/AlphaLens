# Independent static public-demo package

A prepared, unpubished portfolio demo, completely separate from the private
AlphaLens backend.128 original synthetic instruments,90 generated weekday slots;
no actual NSE identities/prices, model artifacts/results, accounts, alerts or
credentials. All generated observations are conspicuously TEST_ONLY_SYNTHETIC.
Weekdays are not presented as an official exchange calendar. Original P6
numerical formulas are applied to generated examples offline; browser charts
are presentation only. No investment recommendation or fabricated live feed.

Landing + interactive candlestick/SMA20/volume/RSI/drawdown/comparison terminal,
heatmap/screener, Evidence Passport example, reliability/methodology/architecture
and limitations. Keyboard controls, themes and mobile layout. CSP connect-src
none; separate entry/build/config, no private API proxy or runtime auth/provider
configuration. No service worker, analytics, external fonts or runtime requests.
External GitHub project link is deliberate navigation, not data acquisition.

## Verified Windows CMD workflow

From the isolated development checkout (or this branch in a future owned checkout):

```cmd
cd /d D:\al-research\p28-worktree
scripts\windows\project-python.cmd -m scripts.build_p29_public_demo --output apps/web/demo/data.json
set "PATH=D:\al-research\p18-runtime\node-v22.23.3-win-x64;%PATH%"
set "ALPHALENS_DEMO_OUTPUT_DIR=D:\al-research\p29-runtime\public-demo"
cd apps\web
npm run build:demo
npm run preview:demo
```

Open http://127.0.0.1:8031; Ctrl+C stops that foreground preview only.
The generated file is already committed; generation is not required every day.
Browser tests use a separate fresh context and optional self-started preview:

```cmd
set "PLAYWRIGHT_BROWSERS_PATH=D:\al-research\p18-runtime\browsers"
npm run test:demo
```

Do not point static hosting at the whole repository, private app output or D:
research directories. Publish only the reviewed demo build directory, including
scoped original-demo MIT licence and retained third-party notices. No private
backend must be opened publicly. Nothing is published or enabled by these scripts.

## Free publication plan and costs

The GitHub repository is public. [GitHub Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)
provides a zero-subscription static-hosting path for a public repository, subject
to its usage limits/terms. Prepared build uses relative asset paths suitable for
an AlphaLens project subpath. A future operator can review and approve publishing
only this static package. No hosting workflow is enabled during this sprint.

AWS deployment is optional and not selected: free-tier eligibility/expiry,
requests, storage, bandwidth, logging and custom-domain costs must be checked
before account/resource creation. No always-free AWS assumption, account change,
paid resource or billing commitment is made. Existing production-security/data
rights restrictions block public deployment of the private research backend;
this isolated synthetic static demonstration does not remove those restrictions.
