"""P4-claude 원본(stream-json)을 공개 저장소용 요약으로 바꾼다. 원본은 저장소 밖에 둔다.

원본의 system/init 이벤트에는 사용자가 설치한 플러그인·스킬·명령과 연결된 외부 서비스의
이름이 모두 있다. 공개 저장소에는 개수와 상태만 올린다.

개수는 init 이벤트가 **알린** 목록의 길이다. 모델에 실제로 보낸 문맥 전체가 아니다. init에
필드가 없으면 0이 아니라 null로 적고 `missing_fields`에 이름을 남긴다 — '아무것도 싣지
않았다'와 '이 버전은 그 필드를 주지 않았다'는 다른 관측이다(PR #4 R05). 원본의 sha256과
이 스크립트의 git blob sha1을 함께 남겨, 원본을 가진 사람이 같은 요약을 다시 만들 수 있게 한다.

    python tools/v04-01/summarize_claude_init.py <tier2/P4-claude.txt> <저장소 밖 원본 보관 경로>
"""
import collections
import hashlib
import json
import pathlib
import shutil
import sys

LIST_FIELDS = ("tools", "mcp_servers", "plugins", "skills", "agents", "slash_commands")


def parse(body: str) -> tuple[dict, dict]:
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
    if init is None or result is None:
        raise ValueError("stream has no system/init or no result event; nothing summarised")
    return init, result


def plugin_origin(plugin) -> str:
    """이름 끝의 '@builtin'이면 Claude Code 내장이다(aux-pc 2.1.280 P4b). 그 밖의 출처 이름은
    사용자 설치 목록을 드러낼 수 있으므로 'other'로만 센다."""
    name = plugin.get("name") if isinstance(plugin, dict) else plugin
    if not isinstance(name, str) or not name:
        return "unknown"
    return "builtin" if name.endswith("@builtin") else "other"


def summarize(init: dict, result: dict, raw_sha256: str, script_sha1: str) -> dict:
    def listed(field):
        value = init.get(field)
        return value if isinstance(value, list) else None

    counts = {field: (None if listed(field) is None else len(listed(field))) for field in LIST_FIELDS}
    tools, servers, plugins = listed("tools"), listed("mcp_servers"), listed("plugins")
    counts["mcp_tools"] = None if tools is None else sum(1 for t in tools if str(t).startswith("mcp__"))
    counts["mcp_servers_by_status"] = None if servers is None else dict(
        collections.Counter(server.get("status") for server in servers))
    counts["mcp_servers_by_origin"] = None if servers is None else dict(collections.Counter(
        "claude.ai connector" if str(server.get("name", "")).startswith("claude.ai ") else "plugin-provided"
        for server in servers))
    counts["plugins_by_origin"] = None if plugins is None else dict(
        collections.Counter(plugin_origin(p) for p in plugins))
    usage = result.get("usage") or {}
    return {
        "note": "Summary of the stream-json run. The raw stream stays on the PC because it lists "
                "the user's installed plugins, skills, commands and connected services. Counts are "
                "what the system/init event announced, not the full prompt sent to the model; "
                "null means the field was absent.",
        "raw_sha256": raw_sha256,
        "summarizer_git_blob_sha1": script_sha1,
        "claude_code_version": init.get("claude_code_version"),
        "model": init.get("model"),
        "permissionMode": init.get("permissionMode"),
        "apiKeySource": init.get("apiKeySource"),
        # 값이 아니라 필드 이름만. 버전마다 무엇을 알리는지 비교할 수 있게 한다.
        "init_fields": sorted(init),
        "init_counts": counts,
        "missing_fields": [field for field in LIST_FIELDS if listed(field) is None],
        "result": {
            "is_error": result.get("is_error"),
            "subtype": result.get("subtype"),
            "result": result.get("result"),
            "input_tokens": usage.get("input_tokens"),
            "cache_creation_input_tokens": usage.get("cache_creation_input_tokens"),
            "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "total_cost_usd_client_estimate": result.get("total_cost_usd"),
        },
    }


def main(argv: list[str]) -> int:
    src, keep = pathlib.Path(argv[0]), pathlib.Path(argv[1])
    raw = src.read_bytes()
    header, body = raw.decode("utf-8").split("\n\n", 1)
    init, result = parse(body)
    script = pathlib.Path(__file__).read_bytes()
    summary = summarize(init, result, hashlib.sha256(raw).hexdigest(),
                        hashlib.sha1(b"blob %d\0" % len(script) + script).hexdigest())
    keep.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, keep)
    src.write_text(header + "\n# stored: summary only (see note)\n\n"
                   + json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
