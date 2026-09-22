"""P4-claude 원본(stream-json)을 공개 저장소용 요약으로 바꾼다. 원본은 저장소 밖에 둔다.

원본의 system/init 이벤트에는 사용자가 설치한 플러그인·스킬·명령과 연결된 외부 서비스의
이름이 모두 있다. 공개 저장소에는 개수와 상태만 올린다.

    python tools/v04-01/summarize_claude_init.py <tier2/P4-claude.txt> <저장소 밖 원본 보관 경로>
"""
import collections
import json
import pathlib
import shutil
import sys

src = pathlib.Path(sys.argv[1])
keep = pathlib.Path(sys.argv[2])
header, body = src.read_text(encoding="utf-8").split("\n\n", 1)
init = result = None
for line in body.splitlines():
    line = line.strip()
    if not line.startswith("{"):
        continue
    event = json.loads(line)
    if event.get("type") == "system" and event.get("subtype") == "init":
        init = event
    elif event.get("type") == "result":
        result = event

mcp = collections.Counter(server.get("status") for server in init.get("mcp_servers", []))
connectors = collections.Counter(
    "claude.ai connector" if server.get("name", "").startswith("claude.ai ") else "plugin-provided"
    for server in init.get("mcp_servers", []))
usage = result["usage"]
summary = {
    "note": "Summary of the stream-json run. The raw stream stays on the PC because it lists "
            "the user's installed plugins, skills, commands and connected services.",
    "claude_code_version": init.get("claude_code_version"),
    "model": init.get("model"),
    "permissionMode": init.get("permissionMode"),
    "apiKeySource": init.get("apiKeySource"),
    "loaded_into_context": {
        "tools": len(init.get("tools", [])),
        "mcp_tools": sum(1 for t in init.get("tools", []) if t.startswith("mcp__")),
        "mcp_servers": len(init.get("mcp_servers", [])),
        "mcp_servers_by_status": dict(mcp),
        "mcp_servers_by_origin": dict(connectors),
        "plugins": len(init.get("plugins", [])),
        "skills": len(init.get("skills", []) or []),
        "agents": len(init.get("agents", []) or []),
        "slash_commands": len(init.get("slash_commands", []) or []),
    },
    "result": {
        "is_error": result.get("is_error"),
        "result": result.get("result"),
        "input_tokens": usage.get("input_tokens"),
        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens"),
        "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "total_cost_usd_client_estimate": result.get("total_cost_usd"),
    },
}
keep.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(src, keep)
src.write_text(header + "\n# stored: summary only (see note)\n\n"
               + json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps(summary, ensure_ascii=False, indent=1))
