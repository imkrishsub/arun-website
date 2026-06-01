# App-it report

**1. Project type detected:**
Static HTML site — `index.html` at repo root, no `package.json`, no build step, no dev server. `favicon.svg` (gold triangle mark). `swiftc` available. Worktree at `arun-website-feat-app-it`; baked `PROJECT_ROOT` points to worktree path — rebuild from main checkout after merge.

**2. Apps detected:** 1
- **Arun.mur** — static HTML, `file://` URL, no server. Multiple `variant-*.html` files are design variants, not separate apps.

**3. Strategy chosen per app:**
- Arun.mur: **A2 static** — Swift WKWebView shell loading `file://$PROJECT_ROOT/index.html`

**4. Why this is the lowest-effort robust approach:**
No server means no port allocation, no startup wait, no warm-daemon complexity. Strategy A1 was ruled out because there's no dev server to start. A2 gives a native Dock icon, single-instance window management, and instant launch. Chrome fallback was ruled out (no FSA real-I/O, no Chromium-only APIs needed).

**5. Files added/changed:**
- `assets/app-icon.svg` — copied from `favicon.svg` (gold triangle brand mark)
- `assets/icons/` — generated icon artifacts (gitignored)
- `desktop/Arun.mur.app/` — built bundle (gitignored)
- `scripts/wrapper.swift`, `scripts/run-template.sh` (A2 static, no server), `scripts/info-plist-template.xml`
- `scripts/desktop-build.sh`, `scripts/desktop-icons.sh`, `scripts/desktop-install.sh`, `scripts/desktop-quit.sh`
- `scripts/app-it.config.json`
- `Makefile` — desktop-build, desktop-icons, desktop-install, desktop-quit targets
- `docs/desktop-launcher.md`, `docs/desktop-launcher.app-it-report.md`
- `.gitignore` — added: `desktop/`, `assets/icons/`

**6. Icon source per app:**
- Arun.mur: `assets/app-icon.svg` (copied from `favicon.svg`) — 32×32 viewBox SVG, gold triangle (#f0b429) on dark background (#0a0e1a), rasterized to 1024×1024 via rsvg-convert. Beat `arun.jpg` (photo, not a mark) as the brand symbol.

**7. To change an app icon later:**
Replace `assets/app-icon.svg`, then `make desktop-icons && make desktop-build && make desktop-install`.

**8. Build / install / quit commands:**
- Build: `make desktop-build`
- Install: `make desktop-install` (→ ~/Applications/App It/)
- Quit: `make desktop-quit` (N/A for static — no daemonized server)

**9. Generated launcher locations:**
- Repo: `desktop/Arun.mur.app`
- Installed: `~/Applications/App It/Arun.mur.app`
- No `server.port` file (static, no server)

**10. Verification (per app):**
- [x] Build succeeded; `.app` exists; wrapper is universal Mach-O (arm64+x86_64); `.icns` is multi-resolution
- [x] Bundle metadata correct — `CFBundleIdentifier=com.user.arun-mur`, `CFBundleName=Arun.mur`, no `__PLACEHOLDER__` leakage
- [x] N/A — static, no server port to record
- [x] N/A — static, no HTTP server
- [x] Single instance; `pgrep -x wrapper` confirms exactly 1 process
- [x] Bundle identity registered (`lsregister` shows `com.user.arun-mur`)
- [x] Cmd+Q (via `osascript`) terminates wrapper process
- [x] Red-X leaves wrapper alive (no server — window-close leaves app in Dock, instant re-activate)
- [x] Re-open from install path works; wrapper starts in <1s (static, no compile step)
- [x] Install-path `open` exits 0; build-path bundle deregistered from LaunchServices
- [ ] needs human: window content, Dock icon identity (gold triangle vs Chrome/Safari icon)
- [ ] needs human: keyboard shortcuts (Cmd+R reload, Cmd+W close, Cmd+-/=/0 zoom)

**11. Dock Stack:**
- [x] `~/Applications/App It/` exists
- [ ] User should drag `~/Applications/App It/` to the right side of the Dock (one-time setup)

**12. Known limitations:**
- Unsigned bundle — Gatekeeper warns on first launch; right-click → Open to bypass.
- WebKit, not Chromium — use Chrome for devtools.
- `PROJECT_ROOT` baked to worktree path — run `make desktop-build && make desktop-install` from main checkout after merge to rebake correct path.
- arm64+x86_64 universal binary.

## Decision history
- 2026-06-01: Initial build (Strategy A2 static, bundle-id com.user.arun-mur, file:// URL, icon: favicon.svg gold triangle). Worktree build — rebuild from main checkout after merge.
