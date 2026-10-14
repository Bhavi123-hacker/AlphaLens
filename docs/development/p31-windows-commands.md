# P31 native Windows operation

Run from PowerShell using the existing configured operator account:

```powershell
cd D:\al-research\p28-worktree
.\scripts\windows\start-p31-alphalens.cmd
```

Open `http://127.0.0.1:8017/login`. The start command starts the existing owned
P30 PostgreSQL instance if needed and serves the P31 compiled UI with the P31
private config. It runs in the foreground; do not start a duplicate listener.
Sign in, search the current NSE master, select an equity and explicitly load
Upstox observations. The independent archive source remains selectable.

From a second PowerShell window, stop the owned application and database:

```powershell
cd D:\al-research\p28-worktree
.\scripts\windows\stop-p31-alphalens.cmd
```

This uses the cooperative authenticated local control and exact checksum-owned
database stop, not process-name termination. Configs, credentials, databases,
research archive and alerts are preserved. A fresh private config can be prepared
from the existing P30 config with `project-python.cmd -m scripts.prepare_p31_runtime`;
this does not reset the operator password. Rebuilding the UI:

```powershell
cd D:\al-research\p28-worktree\apps\web
$env:ALPHALENS_WEB_OUTPUT_DIR='../../.local-data/p31-web-build'
& 'D:\al-research\p18-runtime\node-v22.23.3-win-x64\node.exe' node_modules/typescript/bin/tsc -b
& 'D:\al-research\p18-runtime\node-v22.23.3-win-x64\node.exe' node_modules/vite/bin/vite.js build
```

Retained ingestion, scheduler and inference gates remain unchanged. No source
prices are loaded automatically at start.
