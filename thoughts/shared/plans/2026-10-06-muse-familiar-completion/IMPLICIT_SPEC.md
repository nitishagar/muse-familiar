<!-- SIGNPOST | 1/5: SPEC | requirements only, no designs | Next: PLAN.md
     Pipeline: SPEC -> PLAN -> PLAN_VALIDATION -> implement+review -> tests+TEST_VALIDATION -> green -->

# Implicit Spec — muse-familiar completion (features missing from the released repo)

Seeded from `thoughts/shared/research/2026-10-06-muse-familiar-missing-features.md`
(fresh at HEAD d1995f8; staleness check: only thoughts/ files changed since
its cited commit 2cc19c3). Its Evidence Ledger and Verification Surface
(`thoughts/shared/VERIFICATION_SURFACE.md`) are incorporated by reference.

## Scope-defining requirement

The repo's own public promises become true, and every verified hygiene gap
closes: CI exists and runs the suite + secrets gate + landing regen parity;
a fresh cloner reaches a running creature from the README alone; the
"GitHub / Home Assistant / curl" trio ships ready artifacts; the local CLI
surface matches the Muse command surface (status/feed); Muse command
registration is one command, not a hand-edit runbook; the repo carries
release/community metadata (topics, homepage, tagged release). Nothing
that was never promised is added (see Bounding assumptions).

## Invariants (every one upholds — from research Implicit Spec, unchanged)

1. **No secrets in repo or history** — the secrets gate (all
   `SECRETS_GATE_EXTRA` modes + history scan) must stay green; any new
   file type added to `tools/secrets_gate.py` CODE_EXTS must be re-gated
   in the same change.
2. **MCU-side safety clamps stay authoritative** — ≤4 fps, 3-bit
   grayscale, 30 s idle timeout remain in the sketch; no firmware changes
   in this effort; a killed/hung engine still leaves the matrix dim.
3. **Webhook hardening order preserved** — rate-limit before auth,
   defensive Content-Length, constant-time compare; any new endpoint or
   client (incl. a CLI `feed`) inherits the same order and limits.
4. **Router socket via documented client API only, never re-permissioned.**
5. **Flock discipline** — long-lived writers lock (engine SHARED, upload
   EXCLUSIVE); short-lived user-invoked CLI writes remain the recorded
   exception; no NEW long-lived lockless writer.
6. **Bridge retry must not corrupt show state** — replayed chunk /
   begin-without-play tolerated; sketch 30 s idle timeout is the backstop.
7. **Webhook accounting correct under handler-thread concurrency** — no
   crash/growth introduced; changes must not make the unsynchronized
   `_STATE` worse (exact-vs-approximate limiting is a plan decision to
   state, not to silently change).
8. **Landing stays generated** — docs/index.html + og-image.png remain
   outputs of tools/make_landing.py; a parity check becomes a deliverable
   (research Gap).
9. **Muse spec shape contract** — familiar_specs keep matching the SDK
   COMMAND_SPECS schema; the contract test remains runnable against the
   real SDK (`MUSE_SDK_LINUX_DIR`) and any registration mechanism must
   keep specs single-sourced.
10. **msgpack optional at import; stdlib-only runtime; Python ≥3.10** —
    new code adds no required third-party dependency (CI deps excluded).
11. **Docs copy-paste-runnable** — every command block in README, landing
    quickstart, and COMMANDS.md references only files/vars the repo
    defines or shows how to define; current violations ($KEY,
    `sdk-linux/`, "after installing the unit") are eliminated.
12. **Commit hygiene** — no co-author attribution in any commit.
13. **Board-safety of remote actions** — anything executed on the board
    (service restart, SDK executor patch) must be atomic/reversible
    (backup-first) and must never widen permissions or touch hallpi.

## Edges any change must survive

- Concurrent pokes during CLI `status`/`feed` reads; engine absent
  (status must degrade to a clear report, not a stack trace).
- Partial install: installer re-run must be idempotent (unit, key, SDK
  patch each safely re-runnable; SDK patch skip-if-present + backup +
  syntax check + --remove).
- CI cold runner: no board, no msgpack preinstalled, no SDK checkout —
  suite must be green with contract test skipped cleanly.
- Landing regen on a machine without the venv (stdlib-only generator).
- Rate-limited or unauthenticated `feed` — must fail with the same
  401/429 semantics as any other client, exit non-zero.

## Bounding assumptions (confirmed defaults — user may override later)

- **Scope = promise-completion + verified hygiene gaps.** Sibling-parity
  features (sound/TTS, persistence/growth, personas, custom-frame
  tooling, enclosure STLs, OTA, App Lab distribution) are OUT — never
  promised by this repo; each is a candidate for a future loop.
- **No behavioral config knobs** (mood durations, temperatures) — not
  promised; simplicity guardrail applies. Existing env knobs unchanged.
- **Firmware untouched** — all work is host-side/repo-side; the board
  keeps its deployed sketch and engine; board-facing actions limited to
  service reload + SDK patch install (both reversible).
- **Single-user, single-board** — no multi-tenant concerns.
- **Muse app US-gating** — docs may mention; code cannot fix.
- **MUSE_SESSION_ID**: implemented (env → `--session-id`) rather than
  removed, because COMMANDS.md documents it and the SDK supports it
  natively (pebble example pattern).

## Intent open questions → closure checklist

| Open question (research Intent) | Closure |
|---|---|
| Which features count as "missing"? | Answered: PLAN.md Approach — every repo promise made true + verified hygiene gaps; siblings explicitly deferred (Bounding assumptions) |
| Muse official X handle (social, not repo) | Carried forward — out of repo scope; social pack unchanged except the topics-line correction |
| App Lab distribution feasibility | Answered by omission: out of scope (Bounding assumptions); no Zephyr-core channel found in research |
| Pairing/video/user gates | Carried forward — remain user manual gates (unchanged by this plan) |
