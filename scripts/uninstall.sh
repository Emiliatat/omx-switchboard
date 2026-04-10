#!/usr/bin/env bash
set -euo pipefail

CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
TARGET_DIR="$CODEX_HOME/skills/omx-switchboard"
LEGACY_TARGET_DIR="$CODEX_HOME/skills/omx-router"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"

rm -rf "$TARGET_DIR"
rm -rf "$LEGACY_TARGET_DIR"
rm -f "$BIN_DIR/omxr.py" "$BIN_DIR/omxr" "$BIN_DIR/omx-switchboard" "$BIN_DIR/codex-omx-router"
echo "Removed $TARGET_DIR"
