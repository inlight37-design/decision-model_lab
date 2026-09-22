# Repository orientation

This is a research and architecture repository with offline synthetic checks, not a working multi-provider orchestrator.

- Start with [v0.4 HANDOFF](docs/architecture/v0.4/HANDOFF.md); read only the relevant design and source sections.
- Current architecture: [v0.4](docs/architecture/v0.4/README.md). It adds frontier-model independent reasoning, bounded cross-review and evidence-based synthesis alongside economy routing. Difficult planning and evaluation may also use strong models.
- Preserve [v0.3](docs/architecture/v0.3/README.md) native-harness/accounting foundations and [v0.2](contracts/v0.2/README.md) contracts. Architecture v0.4 is not a production wire-schema upgrade.
- Official native subscription CLIs first; paid API/extra-credit fallback requires opt-in. Antigravity agy is not Gemini CLI. Jev-like components remain optional.
- D10-D18 map to F01-F24 in [new sources](docs/architecture/v0.4/sources.json); D01-D09 and E01-E31 remain in v0.3. Distinguish primary-source inspection, vendor reports, abstract-only evidence and project proposals.
- Read the [evidence follow-up](docs/architecture/v0.4/EVIDENCE_FOLLOWUP.md) for the PAL correction and newly screened research.
- Check [validation scope](docs/architecture/v0.4/VALIDATION.md), the [final review](docs/architecture/v0.4/FINAL_REVIEW.md) and the [external review fixes](docs/architecture/v0.4/REVIEW_FIXES.md). Passing offline tests does not establish model quality, citation truth, actual entitlement, sandbox safety or runtime budget enforcement.
- Run checks from the repository root: `python -m unittest discover -s tests -v` (74 tests). Without `jsonschema` the schema-dependent tests skip rather than fail; a skip is not a pass. [CI](.github/workflows/checks.yml) runs every check on push and pull request.
- Evidence registries obey [contracts/sources.schema.json](contracts/sources.schema.json). Every entry needs a non-empty `limits`/`limitations` and a dating field; write `"published": null` when the date is unknown instead of omitting it.
- Recheck installed versions, effective permissions, authentication/funding and model availability before wiring adapters. Never copy credentials or sensitive raw traces into research artifacts.
- Preserve blind first drafts, unresolved counterevidence and explicit call/quorum limits. Agreement is not verification. Save bounded progress and next steps in commits; do not feed the whole archive into each agent prompt.
