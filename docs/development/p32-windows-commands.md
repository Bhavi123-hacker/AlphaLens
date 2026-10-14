# P32 native Windows operation

Run from CMD. Existing operator authentication and Windows-protected credentials
are reused; no secret belongs in a command or config file.

```bat
cd /d D:\al-research\p28-worktree
scripts\windows\start-p32-alphalens.cmd
```

This starts the exactly owned local PostgreSQL15430 service and the authenticated
loopback application, using `.local-data\p32-runtime\operator-config.json` and
the P32 compiled UI. Open http://127.0.0.1:8017/login. Keep the foreground process
running. From another CMD window, cooperative stop is:

```bat
cd /d D:\al-research\p28-worktree
scripts\windows\stop-p32-alphalens.cmd
```

Stop waits for the owned application to drain, then smart-stops only its owned
PostgreSQL instance. It never kills unrelated Python/PostgreSQL processes.

To rebuild the private UI while the application is stopped:

```bat
cd /d D:\al-research\p28-worktree\apps\web
D:\al-research\p18-runtime\node-v22.23.3-win-x64\node.exe node_modules\typescript\bin\tsc -b
D:\al-research\p18-runtime\node-v22.23.3-win-x64\node.exe node_modules\vite\bin\vite.js build --outDir ../../.local-data/p32-web-build --emptyOutDir
```

The one-time `scripts.prepare_p32_runtime` setup intentionally refuses to overwrite
existing runtime roots. It has already run here. Do not rerun it or reset the
operator to start the app. The old P31 launcher points at the old compiled build.

Personal records live in the protected P32 personal sidecar. Preserve that whole
directory when backing up stopped local user data; do not copy it into public demo
assets. Existing automated recovery-root configuration does not yet include this
new sidecar. Provider prices expire from memory and are not a daily retained dataset.
