"""모델 없이: Codex 참여자가 실행될 때 보일 스킬·MCP 서버·연결 앱·설치된 플러그인을 센다.

참여자 계획과 같은 격리·연결·`-c` 값(tools/w2/codex_prompt_input.participant_values)으로 bubblewrap 안에서
`codex app-server`를 띄우고 initialize → skills/list → mcpServerStatus/list → app/installed → plugin/list만 보낸다.
thread/turn은 시작하지 않는다. 서버가 요청하거나 agent 활동 알림을 보내면 멈춘다. 연결 앱은 ID를 적지 않고 개수만,
플러그인은 설치된 것의 공개 카탈로그 이름만 낸다. 2026-09-25 claude 세션이 카드 #59 뒤에 한 번 돌렸다
(NEXT-SESSION 2절 22의 상시 승인, 실제 로그인 폴더 연결 — E·E2와 같은 방식).

  python3 docs/reviews/2026-09-25-plugin-surface/probe.py   # WSL·Linux에서, 저장소 루트에서, 로그인 셸(bash -l)로
  python3 docs/reviews/2026-09-25-plugin-surface/probe.py --control   # 대조: `features.apps=false`만 뺀다
"""
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "w2")]
from app.cli_executor import SANDBOX_ENV  # noqa: E402
from codex_prompt_input import participant_values  # noqa: E402
from core import env as core_env, isolation  # noqa: E402

HELPER = r'''
import json, os, selectors, subprocess, sys, time
exe, work, *values = sys.argv[1:]
proc = subprocess.Popen([exe, "app-server", *values], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL, bufsize=0)
sel = selectors.DefaultSelector()
sel.register(proc.stdout, selectors.EVENT_READ)
state = {"buf": b"", "deadline": time.monotonic() + 30}

def send(method, params=None, rid=None):
    message = {"method": method}
    if params is not None:
        message["params"] = params
    if rid is not None:
        message["id"] = rid
    proc.stdin.write((json.dumps(message) + "\n").encode())
    proc.stdin.flush()

def receive(rid):
    while True:
        if time.monotonic() > state["deadline"]:
            raise RuntimeError("timeout")
        if b"\n" not in state["buf"]:
            if not sel.select(max(0, state["deadline"] - time.monotonic())):
                raise RuntimeError("timeout")
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                raise RuntimeError("server closed")
            state["buf"] += chunk
            continue
        line, state["buf"] = state["buf"].split(b"\n", 1)
        try:
            message = json.loads(line)
        except ValueError:
            continue
        if "method" in message:
            if "id" in message or str(message["method"]).startswith(("thread/", "turn/", "item/")):
                raise RuntimeError("unexpected server request or agent activity")
            continue
        if message.get("id") == rid:
            if "result" not in message:
                raise RuntimeError(method_names[rid] + " refused")
            return message["result"]

def entries(obj):
    """Every dict that carries a name/id, with its plain flags."""
    found = []
    def walk(o):
        if isinstance(o, dict):
            label = next((o[k] for k in ("name", "id") if isinstance(o.get(k), str)), None)
            if label is not None:
                found.append((label, {k: o[k] for k in ("enabled", "installed", "callable") if isinstance(o.get(k), bool)}))
            for v in o.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    return found

method_names = {1: "skills/list", 2: "mcpServerStatus/list", 3: "app/installed", 4: "plugin/list"}
report = {"inference_requests_sent": 0}
try:
    send("initialize", {"clientInfo": {"name": "dml_plugin_surface", "version": "0.1"},
                        "capabilities": {"experimentalApi": True}}, 0)
    receive(0)
    send("initialized", {})
    send("skills/list", {"cwds": [work]}, 1)
    report["skills"] = sorted({name for name, flags in entries(receive(1)) if flags.get("enabled")})
    send("mcpServerStatus/list", {}, 2)
    report["mcp_named_entries"] = len(entries(receive(2)))   # 서버와 그 도구의 이름 있는 항목을 모두 센다
    send("app/installed", {}, 3)
    apps = [flags for name, flags in entries(receive(3)) if flags]
    report["apps"] = {"installed": len(apps), "enabled": sum(bool(f.get("enabled")) for f in apps),
                      "callable": sum(bool(f.get("callable")) for f in apps)}
    send("plugin/list", {}, 4)
    report["plugins_installed"] = sorted({(name, flags.get("enabled")) for name, flags in entries(receive(4))
                                          if flags.get("installed")})
except RuntimeError as exc:
    report["error"] = str(exc)
finally:
    try:
        proc.stdin.close()
    except OSError:
        pass
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=3)
print(json.dumps(report, ensure_ascii=False))
'''


def main():
    home = os.path.realpath(os.path.expanduser("~"))
    child, _ = core_env.child_env(os.environ)
    exe = os.path.realpath(core_env.resolve("codex", child))
    values = participant_values(home, exe)
    if "--control" in sys.argv[1:]:   # 조회가 도구를 볼 수 있는지 확인하는 대조. 참여자 계획은 이 값을 뺀 적이 없다
        at = values.index("features.apps=false")
        values = values[:at - 1] + values[at + 1:]
    ro, rw, ro_at = isolation.participant_mounts("codex", exe, home)
    with tempfile.TemporaryDirectory(prefix="dml-plugin-surface-") as work:
        box = isolation.Sandbox(work_dir=work, home=home, read_only=ro, read_write=rw, env=SANDBOX_ENV,
                                read_only_at=ro_at)
        result = isolation.run(["/usr/bin/python3", "-c", HELPER, exe, work, *values], box, timeout=45,
                               max_output_bytes=200_000)
    try:
        surface = json.loads(result.stdout)
    except ValueError:
        surface = {"error": "no JSON from helper"}
    print(json.dumps({"codex_release": os.path.basename(os.path.dirname(os.path.dirname(exe))),
                      "participant_config": [v for v in values if v != "-c" and not v.startswith("permissions.")],
                      "state": result.state, "exit": result.exit_code,
                      "tree_confirmed_empty": result.tree_confirmed_empty, "surface": surface},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
