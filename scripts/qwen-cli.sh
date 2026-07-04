#!/usr/bin/env bash
# qwen-cli.sh — Sync and manage Qwen Code agents.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
  echo "Usage: $0 <command>"
  echo ""
  echo "Commands:"
  echo "  sync    Update agents from source"
  echo "  list    List installed Qwen agents"
  echo "  deploy  Prepare distribution (manifest + convert)"
  echo "  fetch   Fast update from remote repository"
}

if [[ $# -lt 1 ]]; then
  usage
else
  case "$1" in
    sync)
      echo "Syncing Qwen agents..."
      "$SCRIPT_DIR/convert.sh" --tool qwen
      "$SCRIPT_DIR/install.sh" --tool qwen --no-interactive
      ;;
    list)
      if [[ -d "$REPO_ROOT/.qwen/agents" ]]; then
        ls -1 "$REPO_ROOT/.qwen/agents" | sed "s/\.md$//"
      else
        echo "No Qwen agents found. Run "$0 sync" first."
      fi
      ;;
    deploy)
      echo "Preparing deployment artifacts..."
      "$SCRIPT_DIR/convert.sh" --tool qwen
      "$SCRIPT_DIR/generate-manifest.sh"
      echo "Done. Ready for deployment."
      ;;
    fetch)
      echo "Fetching latest updates..."
      # Use a safe way to fetch without blocking session
      git fetch --depth 1 origin main
      git reset --hard origin/main
      "$SCRIPT_DIR/qwen-cli.sh" sync
      ;;
    *)
      usage
      ;;
  esac
fi
