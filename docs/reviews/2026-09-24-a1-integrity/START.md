# A1 integrity review — start checkpoint

- Date: 2026-09-24.
- Session: ChatGPT.
- Base: `28a18676842f31cd25a0629b2efdc8c3686b46df` (`main`).
- Branch: `chatgpt/a1-integrity-20260924`.
- User request: review the repository comprehensively, fix justified issues directly with incremental GitHub checkpoints, then continue the tasks in `NEXT-SESSION.md`.
- Access: GitHub connector and an isolated analysis container. Direct Git clone in that container failed DNS resolution. No access to `aux-pc`, `aux-pc-wsl`, production workstation, installed/authenticated provider CLIs or private account state.
- Start observation: GitHub returned no open PRs; its branch collection contained only `main`.
- Boundaries: no model calls; no provider authentication/installation; no paid API fallback; no change to existing machine observations; no automatic merge to main. Preserve native subscription paths, blind drafts, explicit quorum policy and controller authority.

## Plan and restart point

1. Read repository rules, current handoff, architecture/review index, execution core, A1 app, boundary tools and tests.
2. Reproduce concrete integrity/lifecycle gaps with offline tests, then make narrowly scoped source fixes. Preserve the small core rather than replacing it with a framework.
3. Follow the handoff's model-free A1 next step only where it does not require an unresolved user decision.
4. Record checks, limitations, follow-up work and this branch in `NEXT-SESSION.md`; open/update a PR and inspect CI results.

A temporary branch-only snapshot workflow may be used to transfer the **tracked public repository source only** through a GitHub Actions artifact into the isolated analysis container. It must use read-only repository permissions, must not collect environment/credentials/untracked files, and must be removed before this PR is finalized. Existing CI remains unchanged. If interrupted, resume from this checkpoint and the branch's Git log, not from assumptions about the user's PC.
