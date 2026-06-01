# Desktop launcher — Arun.mur

Launches the Arun Murugan portfolio site as a native macOS app from the Dock.

## First launch

1. Right-click the app icon and choose **Open**, then click **Open** in the dialog. macOS will remember and skip this on subsequent launches (Gatekeeper, unsigned bundle).
2. The site loads instantly — it's served locally via `file://`, no network required.

## Build and install

```
make desktop-build    # compiles wrapper + builds Arun.mur.app
make desktop-install  # copies to ~/Applications/App It/
```

Drag `~/Applications/App It/` to the right side of your Dock once to get a Stack.

## After moving the repo

The launcher bakes the repo path at build time. If the repo moves, rebuild:

```
make desktop-build && make desktop-install
```

## To change the icon

Replace `assets/app-icon.svg`, then:

```
make desktop-icons && make desktop-build && make desktop-install
```

## Known limitations

- Unsigned bundle — Gatekeeper warns on first launch (right-click → Open to bypass).
- Uses WebKit, not Chromium. For devtools, open `index.html` in Chrome directly.
- Baked `PROJECT_ROOT` — re-run `make desktop-build` if repo moves.
- arm64 + x86_64 universal binary.
