#!/usr/bin/env bash
# Prepare an Ubuntu (WSL2) distribution for live CLI runs of this repository. Safe to run again.
#   bash tools/setup/setup-wsl.sh [--check] [--latest] [--with-node] [--accept-installer-change]
#
# 1. apt packages (sudo asks for your Linux password): bubblewrap python3 python3-jsonschema git curl
#    ca-certificates, and nodejs with --with-node (only for the screen JavaScript tests).
# 2. The official Codex and Claude Code installers, pinned to the versions of the current observation
#    record (python3 tools/setup/check_setup.py --observed-versions) unless --latest. Each installer is
#    downloaded first and its SHA-256 compared with the copy read on 2026-09-25. If it changed, the
#    script stops and keeps the file so you can read it; rerun with --accept-installer-change.
# 3. Prints the login commands (you run them; this script never logs in) and runs check_setup.py.
#
# --check changes nothing and only reports. No model call. The installers write under your home
# directory (~/.local/bin, ~/.codex, ~/.claude); Codex adds a PATH line to ~/.bashrc.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
check=0 latest=0 node=0 accept=0
for arg in "$@"; do
  case "$arg" in
    --check) check=1 ;;
    --latest) latest=1 ;;
    --with-node) node=1 ;;
    --accept-installer-change) accept=1 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

# Installer copies read on 2026-09-25 (same as the V04-01 record of 2026-09-23).
CLAUDE_URL=https://claude.ai/install.sh
CLAUDE_SHA=3a68d3406cf674e17bed1733a4dcf37805e2e47d87417700007d7e1aa766a944
CODEX_URL=https://chatgpt.com/codex/install.sh
CODEX_SHA=150e3cf675682efeaac115aa3747add3f27887896d04ce6d0b56478d8b428bf6

grep -qi '^ID=ubuntu' /etc/os-release 2>/dev/null || echo "WARNING: not Ubuntu; apt package names may differ" >&2

packages=(bubblewrap python3 python3-jsonschema git curl ca-certificates)
[ "$node" = 1 ] && packages+=(nodejs)
missing=()
for p in "${packages[@]}"; do dpkg -s "$p" >/dev/null 2>&1 || missing+=("$p"); done
if [ ${#missing[@]} -eq 0 ]; then
  echo "ok       apt packages: ${packages[*]}"
elif [ "$check" = 1 ]; then
  echo "missing  apt packages: ${missing[*]}  -> sudo apt-get install -y ${missing[*]}"
else
  echo "install  apt packages: ${missing[*]} (sudo)"
  sudo apt-get update -qq
  sudo apt-get install -y --no-install-recommends "${missing[@]}"
fi

declare -A want=([codex]=latest [claude-code]=latest)
if [ "$latest" = 0 ] && command -v python3 >/dev/null 2>&1; then
  while read -r id version; do [ -n "$id" ] && want[$id]=$version; done \
    < <(python3 "$root/tools/setup/check_setup.py" --observed-versions)
fi

install_cli() {  # name exe url sha target
  local name="$1" exe="$2" url="$3" sha="$4" target="$5" have="" tmp got
  if command -v "$exe" >/dev/null 2>&1; then have="$("$exe" --version 2>/dev/null | head -n 1 || true)"; fi
  if [ -n "$have" ] && { [ "$target" = latest ] || [[ "$have" == *"$target"* ]]; }; then
    echo "ok       $name: $have"
    return 0
  fi
  if [ "$check" = 1 ]; then
    echo "missing  $name ${have:+(have: $have) }-> wants $target: bash tools/setup/setup-wsl.sh"
    return 0
  fi
  tmp="$(mktemp)"
  curl -fsSL "$url" -o "$tmp"
  got="$(sha256sum "$tmp" | cut -d' ' -f1)"
  if [ "$got" != "$sha" ] && [ "$accept" = 0 ]; then
    echo "STOP: $url changed since it was read on 2026-09-25 (sha256 $got)." >&2
    echo "      Read $tmp yourself, then rerun with --accept-installer-change." >&2
    exit 3
  fi
  echo "install  $name $target (installer sha256 ${got:0:12}...)"
  case "$exe" in
    claude) bash "$tmp" "$target" ;;
    codex) CODEX_NON_INTERACTIVE=true sh "$tmp" --release "$target" ;;
  esac
  rm -f "$tmp"
}
install_cli "Codex CLI" codex "$CODEX_URL" "$CODEX_SHA" "${want[codex]}"
install_cli "Claude Code" claude "$CLAUDE_URL" "$CLAUDE_SHA" "${want[claude-code]}"

cat <<'EOF'

Logins are yours to do, in an Ubuntu terminal (the script never logs in or reads credentials):
  claude auth login   # choose the Claude subscription (claude.ai), not an API key
  codex login         # ChatGPT login
Open a new login shell afterwards so ~/.local/bin is on PATH, then check again:
  bash -lc 'python3 tools/setup/check_setup.py'
EOF
echo
cd "$root"
python3 tools/setup/check_setup.py
