"""Public diagnostic output policy: redact identifiers and count private init names.

This is a publication aid, not a guarantee that arbitrary free text is safe. Raw
output stays outside the repository and published summaries still need review.
No environment values or credential files are read here.
"""
from __future__ import annotations

from collections import Counter
import re
from typing import Callable


JWT = re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]*")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    r"sk-(?:ant-|proj-)?[A-Za-z0-9_-]{16,}"
    r"|AIza[0-9A-Za-z_-]{30,}"
    r"|gh[pousr]_[A-Za-z0-9]{30,}"
    r"|github_pat_[A-Za-z0-9_]{30,}"
    r"|eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]*"
    r"|(?i:bearer)\s+[A-Za-z0-9._~+/-]+=*)"
)
UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
LONG_HEX = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{24,}(?![0-9a-fA-F])")
TOKEN = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{40,}(?![A-Za-z0-9_-])")
OPAQUE_TOKEN = re.compile(r"[A-Za-z0-9_-]{24,}")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_USER_NAME = r"(?!<user>(?:[{sep}\"'\r\n]|$))[^{sep}\r\n\"']+"
USER_PATH = re.compile(
    r"(?i)([A-Z]:[\\/]+Users[\\/]+)" + _USER_NAME.format(sep=r"\\/")
    + r"|(/(?:home|Users)/)" + _USER_NAME.format(sep="/"))
_CREDENTIAL_NAME = r"(?:access[_-]?token|refresh[_-]?token|id[_-]?token|api[_-]?key|client[_-]?secret|password|token)"
CREDENTIAL_VALUE = re.compile(
    r"(?i)(\b" + _CREDENTIAL_NAME + r"[\"']?\s*[:=]\s*)(?:\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s,;]+)")
COOKIE = re.compile(r"(?im)(\b(?:set-cookie|cookie|authorization)\s*:\s*)[^\r\n]+")
PRIVATE_KEYS = re.compile(r"(?i)(?:" + _CREDENTIAL_NAME + r"|authorization|cookie|set-cookie)")
LIST_FIELDS = ("tools", "mcp_servers", "plugins", "skills", "agents", "slash_commands")
INIT_METADATA = ("claude_code_version", "model", "permissionMode", "apiKeySource")
INIT_FIELDS = frozenset(LIST_FIELDS + INIT_METADATA + (
    "type", "subtype", "cwd", "session_id", "uuid", "output_style", "fast_mode_state"))
SERVER_STATUSES = frozenset({"connected", "failed", "pending", "disabled", "needs-auth"})


def scrub(text: str, home: str = "", *, opaque_tokens: bool = False) -> str:
    """Mask known credential shapes and personal identifiers, preserving CLI flags.

    Auth error lines additionally use opaque_tokens to retain their existing
    conservative policy for every long word. That mode is unsuitable for help
    text and paths, where long option and package names carry useful evidence.
    """
    homes = {value.rstrip("/\\") for value in (home, home.replace("\\", "/"))} - {""}
    for value in sorted(homes, key=len, reverse=True):
        # A home prefix must end at a path boundary: /home/u is not /home/user.
        text = re.sub(re.escape(value) + r"(?=[\\/\s\"']|$)", "~", text, flags=re.IGNORECASE)
    text = USER_PATH.sub(lambda m: (m.group(1) or m.group(2)) + "<user>", text)
    text = EMAIL.sub("<email>", text)
    text = COOKIE.sub(r"\1<redacted>", text)
    text = CREDENTIAL_VALUE.sub(r"\1<redacted>", text)
    text = JWT.sub("<jwt>", text)
    text = SECRET.sub("<redacted>", text)
    text = LONG_HEX.sub("<hex>", UUID.sub("<uuid>", text))
    text = TOKEN.sub(lambda m: "<token>" if all(re.search(p, m[0]) for p in ("[0-9]", "[a-z]", "[A-Z]"))
                     else m[0], text)
    return OPAQUE_TOKEN.sub("<redacted>", text) if opaque_tokens else text


def make_redactor(home: str) -> Callable[[str], str]:
    return lambda text: scrub(text, home)


def scrub_all(value, home: str = "", *, keep_digests: tuple[str, ...] = (), opaque_tokens: bool = False):
    """Redact every string key/value; only named, well-formed digests are exempt."""
    def visit(item, key=None):
        if isinstance(key, str) and PRIVATE_KEYS.fullmatch(key):
            return "<redacted>"
        if isinstance(item, str):
            if key in keep_digests and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", item):
                return item
            return scrub(item, home, opaque_tokens=opaque_tokens)
        if isinstance(item, dict):
            return {(scrub(k, home, opaque_tokens=opaque_tokens) if isinstance(k, str) else k): visit(v, k)
                    for k, v in item.items()}
        if isinstance(item, (list, tuple)):
            return [visit(v) for v in item]
        return item
    return visit(value)


def claude_init_summary(init: dict) -> dict:
    """One count-only policy for both init exporters; absent/malformed is unknown.

    Server status and origin categories are bounded, so private names cannot
    become keys in the public summary even if a CLI emits an unexpected shape.
    """
    lists = {field: init.get(field) if isinstance(init.get(field), list) else None for field in LIST_FIELDS}
    counts = {field: None if items is None else len(items) for field, items in lists.items()}
    tools, servers, plugins = (lists[field] for field in ("tools", "mcp_servers", "plugins"))

    def name(item):
        value = item.get("name") if isinstance(item, dict) else item
        return value if isinstance(value, str) else ""

    def status(server):
        value = server.get("status") if isinstance(server, dict) else None
        return value if isinstance(value, str) and value in SERVER_STATUSES else "unknown"

    counts["mcp_tools"] = None if tools is None else sum(name(t).startswith("mcp__") for t in tools)
    counts["mcp_servers_by_status"] = None if servers is None else dict(Counter(status(s) for s in servers))
    counts["mcp_servers_by_origin"] = None if servers is None else dict(Counter(
        "claude.ai connector" if name(s).startswith("claude.ai ") else "plugin-provided" if name(s) else "unknown"
        for s in servers))
    counts["plugins_by_origin"] = None if plugins is None else dict(Counter(
        "builtin" if name(p).endswith("@builtin") else "other" if name(p) else "unknown" for p in plugins))
    return {**{key: init.get(key) if isinstance(init.get(key), str) else None for key in INIT_METADATA},
            "init_fields": sorted(key for key in init if key in INIT_FIELDS),
            "unknown_field_count": sum(key not in INIT_FIELDS for key in init), "init_counts": counts,
            "missing_fields": [field for field, items in lists.items() if items is None]}
