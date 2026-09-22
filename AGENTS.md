# Repository orientation

This is a research and architecture repository, not an implemented orchestrator.

- Start with [v0.3 HANDOFF](docs/architecture/v0.3/HANDOFF.md) and read only the relevant design sections.
- Current user priorities: Antigravity, ChatGPT and Claude subscriptions; official native CLI first; paid APIs optional; Jev-like components replaceable.
- Current architecture: [v0.3](docs/architecture/v0.3/README.md). Existing synthetic contracts remain [v0.2](contracts/v0.2/README.md); the architecture version is not a wire-schema upgrade.
- Decisions D01–D09 map to evidence E01–E31 in [sources.json](docs/architecture/v0.3/sources.json). Preserve source versions, limitations and the distinction between observations and project proposals.
- Do not describe synthetic fixtures, external benchmark numbers or documentation checks as local model/runtime validation. Check [validation scope](docs/architecture/v0.3/VALIDATION.md).
- Recheck mutable provider authentication, billing and CLI behavior before implementing an adapter. Never store credentials in research artifacts.
