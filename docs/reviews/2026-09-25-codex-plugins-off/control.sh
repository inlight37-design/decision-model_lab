#!/usr/bin/env bash
# Model-free synthetic control for card #64: does a locally installed plugin's skill reach the model input,
# and does features.plugins=false keep it out? Synthetic HOME only; the user's ~/.codex is never touched.
set -u
T=$(mktemp -d /tmp/dml-plugin-control-XXXXXX)
export HOME="$T"; unset CODEX_HOME
MARK=dmlplugmark7f3a
M="$T/market"
mkdir -p "$M/.agents/plugins" "$M/plugins/dml-probe/skills/$MARK"
cat > "$M/.agents/plugins/marketplace.json" <<EOF
{"name": "dml-local", "interface": {"displayName": "DML Local"},
 "plugins": [{"name": "dml-probe", "source": {"source": "local", "path": "./plugins/dml-probe"},
   "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}, "category": "Productivity"}]}
EOF
cat > "$M/plugins/dml-probe/plugin.json" <<EOF
{"\$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
 "name": "dml-probe", "version": "0.1.0", "description": "Synthetic control plugin for decision-model_lab card 64."}
EOF
cat > "$M/plugins/dml-probe/skills/$MARK/SKILL.md" <<EOF
---
name: $MARK
description: Synthetic marker skill $MARK used only to see whether plugin skills reach the model input.
---
Say $MARK.
EOF
echo "== marketplace add"; codex plugin marketplace add "$M" 2>&1 | tail -3
echo "== plugin add"; codex plugin add dml-probe@dml-local 2>&1 | tail -3
echo "== plugin list"; codex plugin list 2>&1 | grep -i -E "dml|installed|enabled" | head -5
echo "== config sections"; grep -n '^\[' "$T/.codex/config.toml" 2>/dev/null
echo "== cache"; find "$T/.codex/plugins" -maxdepth 5 -type d 2>/dev/null | sed "s#$T#~#" | head -8
render() {  # label, extra args...
  local label=$1; shift
  local out; out=$(timeout 60 codex debug prompt-input "$@" "Say hi." 2>/dev/null)
  local rc=$?
  local n; n=$(printf '%s' "$out" | grep -o "$MARK" | wc -l)
  printf '%-44s exit=%s marker_hits=%s json_chars=%s\n' "$label" "$rc" "$n" "${#out}"
}
echo "== renders"
render "default"
render "features.apps=false" -c features.apps=false
render "features.remote_plugin=false" -c features.remote_plugin=false
render "features.plugins=false" -c features.plugins=false
render "apps off + plugins off" -c features.apps=false -c features.plugins=false
render "plugin disabled by key" -c 'plugins."dml-probe@dml-local".enabled=false'
echo "== exec-style: config.toml hidden (stand-in for --ignore-user-config)"
mv "$T/.codex/config.toml" "$T/.codex/config.toml.off" 2>/dev/null && render "no config.toml" && mv "$T/.codex/config.toml.off" "$T/.codex/config.toml"
rm -rf "$T"
echo "cleaned $([ -e "$T" ] && echo no || echo yes)"
