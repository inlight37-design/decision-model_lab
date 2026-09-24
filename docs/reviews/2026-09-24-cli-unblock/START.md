# CLI unblock — initial checkpoint (2026-09-24)

Authoring session: ChatGPT. Base: `16646b34a508f4fbe4fbbd1e00758eb8223a2d65` (PR #37 merged). Branch: `chatgpt/cli-unblock-20260924`.

The user requests actual fixes and investigation of the remaining limits, authorizes necessary work, and requests intermediate commits. Subscription-only funding, preserved ledgers, explicit isolation/context labels and main's PR/check requirements remain in force. No write-enabled workflow will be used to insert code or commit on behalf of this session.

Observed access: GitHub connector reads and branch creation work. The web container is available (Python 3.13.5), but its direct GitHub network clone failed with DNS resolution failure. The advertised PC terminal bridge requires a task/turn token not supplied in this conversation; no PC/WSL command or installed native CLI has been observed in this session. Do not reinterpret earlier PC observations as missing or failed.

Start checks: main is protected; required checks are `checks (3.12)` and `checks (3.13)`. Open PR collection is empty; branch collection contains only main. Read AGENTS.md, current handoff and collaboration rules. Work from this branch, not main or another session's branch.

Implementation goals, in order:

1. Durable per-ledger launch limits; accurately separate attempted participation, reserved CLI launches and provider token usage; independence-label regression coverage.
2. Provider-specific input directories and a bounded multi-provider dispatch path preserving sealed drafts, atomic reservation and acceptance checks.
3. Re-evaluate claimed CLI limits using primary documentation/source: subscription telemetry, model identity, context evidence and Claude's exact-plan readiness. Never turn incomplete context evidence into independent quorum.
4. Commit changes, regression tests, evidence and an updated NEXT-SESSION.md; inspect exact-head CI. Any unavailable live-PC validation remains explicitly unperformed.

Status at this checkpoint: investigation in progress; no model inference calls, no new server started, no product change yet. Next: read affected source and test files; test supported direct code writes. If a connector write is disallowed, preserve a plain reviewable patch rather than use a privileged workflow.
