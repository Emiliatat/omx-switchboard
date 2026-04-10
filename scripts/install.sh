#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
TARGET_DIR="$CODEX_HOME/skills/omx-switchboard"
LEGACY_TARGET_DIR="$CODEX_HOME/skills/omx-router"
SOURCE_DIR="$REPO_ROOT/skills/omx-switchboard"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"

mkdir -p "$CODEX_HOME/skills"
mkdir -p "$BIN_DIR"
rm -rf "$TARGET_DIR"
rm -rf "$LEGACY_TARGET_DIR"
cp -R "$SOURCE_DIR" "$TARGET_DIR"
cp "$REPO_ROOT/scripts/omxr.py" "$BIN_DIR/omxr.py"
cp "$REPO_ROOT/scripts/omxr" "$BIN_DIR/omxr"
cp "$REPO_ROOT/scripts/omxr" "$BIN_DIR/omx-switchboard"
rm -f "$BIN_DIR/codex-omx-router"
chmod +x "$BIN_DIR/omxr.py" "$BIN_DIR/omxr" "$BIN_DIR/omx-switchboard"

echo "Installed omx-switchboard to $TARGET_DIR"
echo "Installed launchers to $BIN_DIR/omxr and $BIN_DIR/omx-switchboard"
