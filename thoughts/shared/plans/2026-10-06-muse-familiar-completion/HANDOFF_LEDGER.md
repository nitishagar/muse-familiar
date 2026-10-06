# Handoff Ledger — muse-familiar completion

Bundle: thoughts/shared/plans/2026-10-06-muse-familiar-completion/
Plan: 5 phases, medium scale. Validation: MINOR-FAIL→PASS (author-verified
in-place, resume unavailable). Start HEAD: 19e3234.

## Position
- Phase 1 (CI + parity + guards) in progress.

## State changes
- (none yet — implementation starting)

## Decisions
- Reviewer-resume protocol: SendMessage resume failed once ("no active
  local_agent task") → author-verified-in-place PASS used per command rule.

## Hypotheses
- Phase 3 YAML test fail: H=test loader too naive for HA's !secret tag
  (safe_load ConstructorError at home-assistant.yaml:16). Check: the
  failure text. CONFIRMED — test's loader taught the tag (artifact kept
  HA-idiomatic). Note: test written same phase; not a weakened
  pre-existing test.

## Confusion
- Landing generator + tests were overhauled by out-of-session commits
  110ee29/2cc19c3 (banded layout, numbered headers) — plan written against
  current HEAD, but implementer must read the CURRENT make_landing.py.

## Hypotheses (phase 4)
- test_status_healthy fail: H=status over-weighted unit state (NUC systemd
  says inactive for absent user unit) → rc 2 on a healthy dev engine.
  Check: assertion rc==2 + code path review. CONFIRMED — fixed cli.py
  (exit 2 now driven by /health only; unit state is context + hint).

## Hypotheses (phase 5)
- muse_install tests red (KeyError executor_verify): H=hook relied on
  sys.modules[__name__] which fresh-file loads don't populate. CONFIRMED —
  register() now takes globals() (dict+class patching propagate).
- force-then-remove left a backup: two same-second installs collided on
  backup name (clobber) + --remove didn't delete baks[0]. CONFIRMED both —
  backup names counter-suffixed; --remove deletes all backups.

## Decisions (phase 5)
- v0.1.0 tag + GitHub Release happen AFTER impl/test/security reviews pass
  (release tags reviewed code); plan criterion partially ticked, release
  step pending reviews.

## Open
- Board manual gates (installer run, muse install.py run, familiar
  status/feed live) deferred to user per plan.
