#!/bin/bash
# app-it static launcher (A2) — opens index.html via file:// URL.
# No dev server. __START_COMMAND__ and __PORT__ are substituted but unused.

set -e

APP_NAME="__APP_NAME__"
APP_SLUG="__APP_SLUG__"
PROJECT_ROOT="__PROJECT_ROOT__"
POLYFILL_PATH="__POLYFILL_PATH__"

# PATH augmentation (Finder/Dock launches start with bare PATH=/usr/bin:/bin)
NVM_BIN=""
if [ -d "$HOME/.nvm/versions/node" ]; then
    LATEST_NVM_NODE="$(ls -1 "$HOME/.nvm/versions/node" 2>/dev/null | sort -V | tail -1)"
    [ -n "$LATEST_NVM_NODE" ] && NVM_BIN="$HOME/.nvm/versions/node/$LATEST_NVM_NODE/bin"
fi
export PATH="$HOME/.bun/bin:$HOME/.deno/bin:$HOME/.volta/bin:$HOME/.local/share/mise/shims:$HOME/.asdf/shims:$HOME/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:${NVM_BIN}:$HOME/Library/pnpm:$PATH"

if [ ! -d "$PROJECT_ROOT" ]; then
    /usr/bin/osascript -e "display alert \"$APP_NAME failed to launch\" message \"Project repo not found at:\n$PROJECT_ROOT\n\nRe-run scripts/desktop-build.sh from the repo.\""
    exit 1
fi

INDEX="$PROJECT_ROOT/index.html"
if [ ! -f "$INDEX" ]; then
    /usr/bin/osascript -e "display alert \"$APP_NAME failed to launch\" message \"index.html not found:\n$INDEX\""
    exit 1
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
WRAPPER="$HERE/wrapper"
if [ ! -x "$WRAPPER" ]; then
    /usr/bin/osascript -e "display alert \"$APP_NAME failed to launch\" message \"Native wrapper missing at:\n$WRAPPER\n\nRun: make desktop-build\""
    exit 1
fi

# Static (A2): pass empty strings for port and pid-file — no server to manage.
exec "$WRAPPER" "file://$INDEX" "$APP_NAME" "" "" "$POLYFILL_PATH"
