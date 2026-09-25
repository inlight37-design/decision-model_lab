#!/usr/bin/env bash
# Prepare an Ubuntu (WSL2) distribution for live CLI runs of this repository. Safe to run again.
#   bash tools/setup/setup-wsl.sh [--check] [--latest] [--with-node] [--apt-only] [--no-final]
#                                 [--accept-installer-sha <codex|claude>=<sha256>]...
#
# 1. apt packages (as root no sudo; otherwise sudo asks for your Linux password): bubblewrap python3
#    python3-jsonschema git curl ca-certificates, and nodejs with --with-node (screen JavaScript tests only).
# 2. The official Codex and Claude Code installers, pinned to the exact versions of the current observation
#    record (python3 tools/setup/check_setup.py --observed-versions). If that record cannot be read the
#    script stops; it never falls back to the newest versions by itself. --latest asks for them on purpose.
#    An installer must match the SHA-256 you approved: by default the copy read on 2026-09-25. A different
#    download is kept under ~/.cache/dml-setup/ and the script stops. After reading that file, rerun with
#    --accept-installer-sha <codex|claude>=<its sha256>: exactly those bytes run, never a newer download.
# 3. Prints the login commands (you run them; this script never logs in) and runs check_setup.py.
#
# tools/setup/setup.ps1 (Windows, one touch) calls it twice: as root with --apt-only, then as your user
# with --no-final. --check changes nothing and only reports. No model call.
# Exit codes: 0 done, 2 bad option or run as root, 3 installer differs from the approved hash,
# 4 observed versions unreadable, 5 a download or install failed, otherwise check_setup.py's code.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
check=0 latest=0 node=0 apt_only=0 final=1
declare -A approved=()
while [ $# -gt 0 ]; do
  case "$1" in
    --check) check=1 ;;
    --latest) latest=1 ;;
    --with-node) node=1 ;;
    --apt-only) apt_only=1 ;;
    --no-final) final=0 ;;
    --accept-installer-sha)
      if [ $# -lt 2 ]; then echo "--accept-installer-sha needs <codex|claude>=<sha256>" >&2; exit 2; fi
      case "$2" in codex=*|claude=*) ;; *) echo "--accept-installer-sha takes codex=<sha256> or claude=<sha256>" >&2; exit 2 ;; esac
      value="${2#*=}"
      if ! [[ "$value" =~ ^[0-9a-f]{64}$ ]]; then echo "not a lowercase sha256: $value" >&2; exit 2; fi
      approved[${2%%=*}]=$value
      shift ;;
    -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

# Installer copies read on 2026-09-25 (same as the V04-01 record of 2026-09-23).
CLAUDE_URL=https://claude.ai/install.sh
CLAUDE_SHA=3a68d3406cf674e17bed1733a4dcf37805e2e47d87417700007d7e1aa766a944
CODEX_URL=https://chatgpt.com/codex/install.sh
CODEX_SHA=150e3cf675682efeaac115aa3747add3f27887896d04ce6d0b56478d8b428bf6
VERSION_RE='^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$'

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
  as_root=(sudo)
  [ "$(id -u)" = 0 ] && as_root=()
  echo "install  apt packages: ${missing[*]}${as_root:+ (sudo)}"
  "${as_root[@]}" apt-get update -qq
  "${as_root[@]}" apt-get install -y --no-install-recommends "${missing[@]}"
fi
if [ "$apt_only" = 1 ]; then exit 0; fi
if [ "$(id -u)" = 0 ]; then
  echo "STOP: the CLIs install into a user's home; run this as your Linux user, not root." >&2
  exit 2
fi

# The exact versions to install. A failed or partial read stops here: silently choosing the newest
# versions would install something no observation covers (2026-09-25 external review R02).
declare -A want=()
if [ "$latest" = 1 ]; then
  want[codex]=latest
  want[claude-code]=latest
else
  if ! observed="$(python3 "$root/tools/setup/check_setup.py" --observed-versions)"; then
    echo "STOP: could not read the observed versions (python3 tools/setup/check_setup.py --observed-versions)." >&2
    echo "      Fix the observation record, or rerun with --latest to install the newest versions on purpose." >&2
    exit 4
  fi
  while read -r id version; do
    if [ -n "${id:-}" ]; then want[$id]=$version; fi
  done <<< "$observed"
  for id in codex claude-code; do
    if ! [[ "${want[$id]:-}" =~ $VERSION_RE ]]; then
      echo "STOP: the observation record has no usable version for $id ('${want[$id]:-}')." >&2
      exit 4
    fi
  done
fi

version_of() {  # the x.y.z a CLI reports, or nothing
  { "$1" --version 2>/dev/null || true; } | grep -oE '[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?' | head -n 1 || true
}

cache="${XDG_CACHE_HOME:-$HOME/.cache}/dml-setup"
install_cli() {  # name exe url reviewed-sha target
  local name="$1" exe="$2" url="$3" reviewed="$4" target="$5"
  local bin have expected file tmp got now
  bin="$(command -v "$exe" || true)"
  have=""
  if [ -n "$bin" ]; then have="$(version_of "$bin")"; fi
  if [ -n "$have" ] && { [ "$target" = latest ] || [ "$have" = "$target" ]; }; then
    echo "ok       $name $have"
    return 0
  fi
  if [ "$check" = 1 ]; then
    echo "missing  $name ${have:+(have $have) }-> wants $target: bash tools/setup/setup-wsl.sh"
    return 0
  fi
  # Approval names bytes, not a URL: only a file whose SHA-256 was approved ever runs (external review R03).
  expected="${approved[$exe]:-$reviewed}"
  mkdir -p "$cache"
  file="$cache/$exe-install-$expected.sh"
  if [ ! -f "$file" ] || [ "$(sha256sum "$file" | cut -d' ' -f1)" != "$expected" ]; then
    tmp="$(mktemp "$cache/$exe-download.XXXXXX")"
    if ! curl -fsSL "$url" -o "$tmp"; then
      rm -f "$tmp"
      echo "STOP: could not download $url" >&2
      exit 5
    fi
    got="$(sha256sum "$tmp" | cut -d' ' -f1)"
    if [ "$got" != "$expected" ]; then
      mv -f "$tmp" "$cache/$exe-install-$got.sh"
      echo "STOP: $url is not the installer you approved (its sha256 is $got)." >&2
      echo "      Read $cache/$exe-install-$got.sh. To run exactly that file, rerun with:" >&2
      echo "      --accept-installer-sha $exe=$got" >&2
      exit 3
    fi
    mv -f "$tmp" "$file"
  fi
  if [ "$(sha256sum "$file" | cut -d' ' -f1)" != "$expected" ]; then
    echo "STOP: $file changed before it could run." >&2
    exit 3
  fi
  echo "install  $name $target (installer sha256 ${expected:0:12}...)"
  case "$exe" in
    claude) bash "$file" "$target" ;;
    codex) CODEX_NON_INTERACTIVE=true sh "$file" --release "$target" ;;
  esac || { echo "STOP: the $name installer failed." >&2; exit 5; }
  bin="$(command -v "$exe" || echo "$HOME/.local/bin/$exe")"
  now="$(version_of "$bin")"
  if [ -z "$now" ] || { [ "$target" != latest ] && [ "$now" != "$target" ]; }; then
    echo "STOP: after installing, $name reports '${now:-no version}', not $target." >&2
    exit 5
  fi
}
install_cli "Codex CLI" codex "$CODEX_URL" "$CODEX_SHA" "${want[codex]}"
install_cli "Claude Code" claude "$CLAUDE_URL" "$CLAUDE_SHA" "${want[claude-code]}"

[ "$final" = 1 ] || exit 0
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
