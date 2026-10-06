---
date: 2026-10-06T15:58:00+05:30
researcher: ZCode
git_commit: 2cc19c3121aa84fc6fd7db5f8a672ace45f30d52
branch: main
repository: git@github.com:nitishagar/muse-familiar.git
topic: "On what all features are missing [from muse-familiar] and create a research with spawned agents to complete the features"
tags: [research, codebase, missing-features, gap-analysis, ci, packaging, examples, muse-integration]
scale: medium
status: complete
last_updated: 2026-10-06
last_updated_by: ZCode
---

# Research: muse-familiar missing-features gap analysis

## Research Question

"On what all features are missing and create a research with spawned agents
to complete the features. Then run parallel sessions with
/create_plan_generic_v2_7 finally with /implement_plan_v2_7 to push updates
after testing without co-author attribution."

## Intent

> Lifted from the ticket/user; `not stated` where silent.

- **Problem**: muse-familiar is released public (repo + live landing), but
  which features are missing to consider the project complete is unknown and
  undocumented.
- **Proposed outcome**: a research-derived inventory of missing features,
  feeding /create_plan_generic_v2_7 → /implement_plan_v2_7 that implements
  them and pushes after testing.
- **Constraints**: push updates **without co-author attribution**; testing
  before push; (standing session constraints: no secrets in repo/history,
  MIT license intact, Muse gadget token and board credentials never
  committed, no touching hallpi, router socket never widened).
- **Open questions**: the user did not enumerate which features count — the
  set must be derived from evidence (promises vs. delivery, first-run
  friction, OSS-hygiene norms, sibling-project parity, deferred items in
  the thoughts/ trail). Which subset the plan implements is the plan's
  call; this doc must enumerate candidates with evidence.

## Summary

The released repo is functionally complete on the board (engine, hardened
webhook, chunked bridge, Muse specs, kill-tested service per trail evidence
[R] — not re-run this session) but incomplete as an open-source product.
Verified gaps cluster in six areas: (1) zero CI and zero
release/community artifacts (no workflows, tags, releases, topics,
homepage, CONTRIBUTING/SECURITY, issue templates); (2) a broken first-run
path — the README's unit-install step is a dangling comment, the unit
hardcodes `$HOME/muse-familiar`, teardown references a `sdk-linux/` dir not
in the repo, and the landing quickstart uses an undefined `$KEY`; (3) the
"GitHub / Home Assistant / curl" feed trio promises two integrations the
repo ships no artifacts for; (4) the creature's behavior is hardcoded — a
partial env-knob set exists (lock, events file, key, router socket, RPC
timeout, upload port) but no mood/timing/temperature configuration, no
config file, no `status`/`feed` CLI, stale README test count; (5) Muse
command registration is a manual executor-patch runbook with no drop-in
packaging, `MUSE_SESSION_ID` is documented but unimplemented, and the
upstream-contract test — the only Muse-spec oracle — is skipped by default
(`MUSE_SDK_LINUX_DIR` unset); (6) verification is manual-only (no CI runs
tests/gate; landing↔frames regen parity, SDK drift, docs copy-paste
runnability, and commit-trailer hygiene all lack an observing check).
Sibling projects treat installer, ready-made GitHub Action, sound/TTS,
and persistent pet-state as table stakes. No single hard core:
the gap list decomposes into ~6 independent small features.

## Detailed Findings

### CI, release & repo-hygiene seam

- No `.github/` directory at all — no workflows, issue/PR templates,
  dependabot, FUNDING [V: `find . -name .github` empty; agent A].
- Zero git tags (`git tag | wc -l` = 0); zero GitHub Releases
  (`gh api …/releases` length 0); `pyproject.toml:3` version 0.1.0 [V].
- Repo metadata empty: topics `[]`, homepage URL unset, Discussions off,
  Wiki off, security policy off (`gh repo view --json`) [V].
- CONTRIBUTING.md / CODE_OF_CONDUCT.md / SECURITY.md / SUPPORT.md absent
  everywhere and never in history [V: find + agent A reflog scan].
- Secrets gate (`tools/secrets_gate.py:104-142`) is manual-only: no git
  hook (only `*.sample` in `.git/hooks/`), no CI step [V].
- `tests/test_landing.py` (4 tests) pins hero centering, mood/kind control
  groups, band layout, OG text geometry — but never regenerates
  `docs/index.html` and diffs, so landing↔frames.py parity is unobserved
  [V: read test_landing.py:1-50].

### First-15-minutes / install / packaging seam

- `README.md:42` verbatim: `systemctl --user enable --now familiar-engine
  # after installing the unit` — repo-wide grep finds NO instruction for
  installing the unit anywhere (README, landing, COMMANDS.md, units/*) [V].
- `units/familiar-engine.service:7-10` hardcodes repo at
  `%h/muse-familiar`, uv at `%h/.local/bin/uv`, key at
  `%h/.config/familiar/key` — works only when cloned to `$HOME/muse-familiar` [V: agent excerpt].
- `pyproject.toml` has NO `[project.scripts]` — no `familiar` console
  command; CLI is `python3 -m familiar.cli` with sys.path bootstrap
  (`familiar/cli.py:16-17`); `serve` duplicates engine args
  (`familiar/cli.py:46-47`) [V].
- `README.md:76-78` teardown references `sdk-linux/install.sh --uninstall`
  — `sdk-linux/` is not in the repo (assumes an SDK checkout) [V: agent B].
- `firmware/upload.sh:2` verbatim: "# FramePlayer build+upload — runs ON
  THE BOARD." — requires board-local arduino-cli + Zephyr core +
  `UNOQ_UPLOAD_PASSWORD` (upload.sh:11,18,21-27); no prebuilt .bin ships;
  no host-side flash path [V: agent B].
- Landing quickstart drift vs README: `docs/index.html:140-144` omits
  key-gen/chmod/unit steps, uses undefined `$KEY`, elides engine start to
  a comment [V: agent B].

### Examples / integrations seam

- Feed trio promised at `README.md:12,20` and `docs/index.html:130` — only
  curl examples exist (`README.md:45-47,54`); no GitHub Actions workflow
  yaml, no Home Assistant automation yaml anywhere in tree [V].

### Creature / engine feature seam

- 7 moods (idle 4f, happy 2f, sad 2f, alert 2f, sleepy 3f, curious 4f,
  off 1f) and 11 event kinds (`KIND_TO_MOOD`, `familiar/frames.py:119-131`)
  — all literals; no config file loads frames/moods [V: agent C excerpt
  matches session knowledge].
- Hardcoded: `MOOD_HOLD_S` (`familiar/moods.py:10-17`), HEARTBEAT_S=20,
  SKETCH_IDLE_TIMEOUT_S=30, HEALTH_POLL_S=60, SLEEPY_TEMP_C=78
  (`familiar/engine.py:30-38`). Env knobs that DO exist (operational, not
  behavioral): `FAMILIAR_LOCK`/`FAMILIAR_EVENTS_FILE` (`engine.py:32,36`),
  `FAMILIAR_KEY` (`webhook.py:120-121`), `FAMILIAR_ROUTER_SOCK`/
  `FAMILIAR_RPC_TIMEOUT` (`bridge_client.py:28,30`), `FAMILIAR_LOCK`/
  `FAMILIAR_UPLOAD_PORT` (`upload.sh:9,21`) — no mood/timing/temperature
  knob, no config file [V: grep].
- CLI subcommands: ping/show/clear/moods/serve only (`cli.py:31-39`) — no
  `status` (health/logs), no local `feed` (an event requires curl+key
  against /poke) [V].
- `README.md:88` claims "19 host-side tests" — actual 28 collected
  (27 pass + 1 skip) [V].
- `README.md:91-96` "GIF / demo shot list" (7 items) — zero GIF/video
  assets in repo (only docs/og-image.png) [V].

### Muse-integration seam

- Registration is a manual patch: `muse_integration/COMMANDS.md:20-54` —
  hand-edit `/opt/musegadget/venv/.../executor.py`, merge FAMILIAR_SPECS,
  hand-write VALIDATED branches; `familiar_specs.py` ships SPECS only, no
  drop-in/automated merge [V: agent C excerpt].
- `COMMANDS.md:65` documents `MUSE_SESSION_ID`; engine code never
  references it (`engine.py` Narrator sends without session) [V: agent C].
- Narrator: synchronous subprocess in single-threaded loop, 100 s timeout
  (accepted limitation; hung musegadget dims creature to idle glyph)
  [R: IMPLEMENTATION_VALIDATION.md:125-128].
- Contract test validates against the REAL upstream executor but **skips
  unless `MUSE_SDK_LINUX_DIR` is set** (`tests/test_contract.py:14-16`) —
  it is the "1 skipped" in every default run, so the Muse-spec oracle is
  dark by default and SDK drift is unobserved [V].
- Narrator: synchronous subprocess in the single-threaded loop with
  `timeout=10` and a "must never stall the heartbeat" comment
  (`engine.py:88`) — the trail's old "100 s timeout" limitation
  (IMPLEMENTATION_VALIDATION.md:125-128) is stale; current risk window is
  10 s per narration [V: code over trail].
- `familiar/cli.py` (incl. the `serve` arg duplication) and the engine
  `Narrator` have zero test references — untested seams [V: grep].
- Phone pairing remains a user manual gate (board shows paired: no until
  `sudo musegadget pair` + app) [R: HANDOFF_LEDGER.md:12-13].

### verification seam

- Full surface persisted at `thoughts/shared/VERIFICATION_SURFACE.md`
  (created by this research): test-all/test-one/gate/regen/flash/kill-test
  commands, oracles (FakeRouter, contract test, landing tests, gate),
  observability (no logging; journal + state files only), gaps (regen
  parity, sketch-constant drift, SDK drift, no CI, pixel gate) [V].
- Suite: 28 collected, 27 passed + 1 skipped at HEAD 2cc19c3
  (`uv run --with pytest --with msgpack`) [V: run this session].
- Cold clone degrades silently without msgpack (whole engine module skips,
  `tests/test_engine.py:19`) [V].
- README documents no test/dev command at all (no pytest/uv mention) [V: agent A grep].

### Deferred items recorded in the thoughts/ trail (candidates)

- Pixel-level visual assertion + release video (human gates)
  [R: PLAN.md:41,57,87; HANDOFF_LEDGER.md:13].
- Kill-test weaknesses: no physical LED-brightness oracle in port; snapshot
  diff is file-list not content hashes; "idle timeout demonstrated"
  overstates [R: IMPLEMENTATION_VALIDATION.md:116-120,201-204].
- Test residuals never added: behavioral chunk pin, LOCK_PATH monkeypatch,
  sketch IDLE_TIMEOUT_MS cross-pin, garbage-key loose 200 arm
  [R: TEST_VALIDATION.md:219-233].
- Waived doc drift: PLAN.md:29 argv hedge; Phase-1 "permissive" license
  wording [R: PLAN_VALIDATION.md:119,127-129].
- Already fixed at HEAD (trail listed them open; verified gone): webhook
  key-error text no longer says "(FAMILIAR_KEY)" (`webhook.py:123` "shared
  key required") and `frames._offset_rows` no longer exists [V: grep] —
  stale trail entries, kept here so the plan does not re-fix them.
- Narrator timeout: trail says 100 s; code says `timeout=10`
  (`engine.py:88`) — stale trail, corrected above [V].

### Sibling-parity baseline (web-sourced, [R])

Applicable-and-absent (candidates, evidence-cited in Evidence Ledger):
TTS spoken replies via USB audio (wupsbr/waveshare-muse-gadget-sdk); OTA
self-update (same); install.sh + env-file config (vocino/muse-arr);
AGENTS.md convention (facebookincubator/muse-gadget-sdk); persona packs
(Muse-charm-mosaico); persistent pet state + autonomous stat decay
(cifertech/TamaFi, socquique/TamaPoke); sprite/frame asset pipeline
(TamaPoke); ready-made GitHub Action (t04glovern build-status-light);
multi-source event monitor (todbot/blink1); enclosure STLs (Sablina,
TamaPoke); App Lab distribution + web dashboard via bridge RPC
(kartben/zephyr_unoq_demo, docs.arduino.cc). Not applicable: touch input,
onboard mic push-to-talk, phone companion app (Muse app fills that role),
ESPHome.

## Implicit Spec — invariants any change here must uphold

> Requirements, not designs.

- **No secrets in repo or history** — token/passwords/WiFi never committed;
  the secrets gate (incl. `SECRETS_GATE_EXTRA` modes and history scan) must
  stay green in CI wherever it runs (`tools/secrets_gate.py:104-142` [V]).
  Edge: any new file type added to CODE_EXTS must be re-gated.
- **MCU-side safety clamps remain authoritative** — ≤4 fps, 3-bit
  grayscale, 30 s idle timeout live in the sketch and must not move to the
  Linux side (`firmware/FramePlayer/FramePlayer.ino`; pinned partially by
  engine constants `engine.py:31` [V]). Edge: a killed/hung engine must
  still leave the matrix dim (idle glyph), never strobing.
- **Webhook hardening order preserved** — rate-limit before auth,
  Content-Length validated defensively, constant-time key compare
  (`familiar/webhook.py:68-95`; pinned by tests/test_engine.py [V]). Any
  new endpoint (e.g. status) inherits the same order.
- **Router socket consumed via documented client API only, never
  re-permissioned** (`/var/run/arduino-router.sock` world-writable; read-only
  use pinned by tests/test_meta.py [V]).
- **Single-writer flock discipline** — long-lived/display-owning writers
  take the lock: engine holds LOCK_SH for life; upload takes LOCK_EX
  (`engine.py:149-150`, `upload.sh:14-15` [V]). Short-lived user-invoked
  CLI writes (`familiar show`/`clear`, `units/display_reset.sh`) are a
  recorded exception that runs lockless by design [R:
  IMPLEMENTATION_VALIDATION.md:167; V: no flock in cli.py]. Edge: any NEW
  long-lived writer must take LOCK_EX or document its exception.
- **Bridge retry must not corrupt show state** — the client retries once
  on socket death and can replay a chunk after reconnect; the sketch's
  chunked-show protocol must tolerate replayed/duplicate chunks, and a
  begin-without-play partial sequence must not leave the matrix mid-show
  beyond the 30 s idle-timeout backstop (`bridge_client.py` reconnect;
  `engine.py:30` backstop comment [V]).
- **Webhook accounting must stay correct under handler-thread
  concurrency** — ThreadingHTTPServer handler threads mutate module-global
  `_STATE["hits"]`/counters unsynchronized today (`webhook.py:24-34` [V]
  observed); any change must not introduce crashes or unbounded growth
  under concurrent pokes, and limiting accuracy requirements (exact vs
  approximate) must be stated by the plan.
- **Landing stays generated** — `docs/index.html` remains the output of
  `tools/make_landing.py` importing `familiar/frames.py` [V]; hand-edits
  would fork the art. (A parity check is a Gap, not an existing invariant.)
- **Muse spec shape contract** — `muse_integration/` specs keep matching
  the SDK COMMAND_SPECS schema (schema/desc/required/optional keys)
  (`tests/test_contract.py` imports the REAL upstream executor but runs
  only with `MUSE_SDK_LINUX_DIR` set — it is skipped by default [V]);
  upstream drift is therefore unobserved in default runs (Gap).
- **msgpack stays optional at import time** — `familiar.bridge_client`
  imports without msgpack; engine tests skip cleanly, never error
  (`tests/test_engine.py:19`, `tests/test_meta.py:16` [V]).
- **Stdlib-only runtime, Python ≥3.10** (`pyproject.toml:5-6` [V]) — msgpack
  remains the single lazy extra, supplied by the unit's `uv run --with`.
- **Docs must be copy-paste-runnable** — every command block in README,
  landing quickstart, and COMMANDS.md must reference only files/vars the
  repo defines or shows how to define (current violations: `$KEY`,
  `sdk-linux/`, "after installing the unit") [V: findings above].
- **Commit hygiene (user constraint)** — no co-author attribution in any
  commit this effort pushes.
- **Bounding assumptions**: single-board hobby scale (no multi-tenant
  concerns); Muse app availability US-gated (docs may mention, code cannot
  fix); firmware distribution stays source-build (no signed prebuilt
  binaries until Arduino's channel exists for Zephyr-core sketches).

## Workload & Scale Envelope

> Facts a cost model needs; hobby-scale envelope stated so the planner
> does not over-engineer.

- **Hot operations**: webhook /poke — ≤12 req/min per key (rate limit,
  `webhook.py:19-22` [V]); bridge show — ≤1 mood change per event, chunked
  2 frames/message (`bridge_client.py` CHUNK_FRAMES=2 [V]); heartbeat
  re-show every 20 s; health poll every 60 s (`engine.py:30-38` [V]).
- **Data categories**: frame = 104 chars (`frames.py` FRAME_LEN [V]); mood
  ≤8 frames, typical 2-4 [V]; webhook body ≤2048 B (`webhook.py` [V]);
  event queue ≤8 (drop-oldest) [V]; router message cap ~256 B
  (`firmware/BRIDGE_FACTS.md` [V]); events JSONL + narration JSONL append
  -only under `~/.local/state/` [V]. Distribution: events are bursty,
  human/CI-triggered, minutes apart — no heavy-tail concern.
- **Envelope**: single board, single user; bridge RTT ~19 ms measured
  (`BRIDGE_FACTS.md` [V doc, R measurement]); matrix 8×13 monochrome-blue,
  8-level grayscale [V]. **No latency baseline is measured anywhere in the
  repo** (webhook handling, narration send RTT unnumbered — gap); scale
  target: none stated (hobby OSS). Assumption — feature work should not
  add blocking work to the engine loop (Narrator already runs sync
  in-loop, 10 s worst case [V]).

## Verification Surface

> Persisted at `thoughts/shared/VERIFICATION_SURFACE.md` (created by this
> research) — see that file for commands/oracles/fixtures/gaps. Headline:
> test-all `uv run --with pytest --with msgpack python -m pytest -q`
  (healthy: 27 passed, 1 skipped); test-one via standard pytest selector;
  gate `python3 tools/secrets_gate.py`; regen `python3
  tools/make_landing.py`; **contract oracle activation: set
  MUSE_SDK_LINUX_DIR=<muse-gadget-sdk>/linux (expect 28 passed)**;
  board-only `firmware/upload.sh` + `units/kill_test.sh` (KILLTEST-OK).
  **Gaps**: no CI at all; the contract test (only Muse-spec oracle) skips
  by default; landing↔frames parity, sketch-constant drift, docs
  copy-paste runnability, commit-trailer hygiene (no-co-author), and
  webhook-thread accounting all lack any observing check; pixel
  correctness stays a human gate.

## Hard Cores

> Inventory only — no sequencing/scoping here.

No single hard core. ~6 independent, individually small features:
(1) CI + release/repo-metadata artifacts, (2) first-run path (unit
installer + entry points + quickstart sync), (3) examples library (GitHub
Action, HA automation), (4) engine behavioral configurability + CLI
status/feed, (5) Muse drop-in packaging of familiar_specs (+ making the
contract oracle runnable by default), (6) sibling-parity feature
extensions (sound/TTS, persistence, personas — each optional,
evidence-cited; note config-via-env is PARTIALLY present already, see
env-knob finding).

## Evidence Ledger

| Claim | Evidence | Trust | Load-bearing |
|---|---|---|---|
| No .github/, no CI, no templates | find tree [V] | V | yes |
| 0 tags, 0 releases, topics [], homepage unset, Discussions/Wiki/sec-policy off | git tag + gh api/view [V] | V | yes |
| No CONTRIBUTING/SECURITY/SUPPORT/CoC anywhere | find + history scan (agent A) | V | yes |
| Unit-install step dangling | `README.md:42` + repo-wide grep [V] | V | yes |
| Unit hardcodes %h/muse-familiar | `units/familiar-engine.service:7-10` (agent excerpt) | V | yes |
| No [project.scripts]; CLI via python -m | `pyproject.toml` [V], `cli.py:16-17,46-47` | V | yes |
| Teardown references absent sdk-linux/ | `README.md:76-78` [V] | V | yes |
| upload.sh board-only; no prebuilt firmware | `upload.sh:2,11,18,21-27`, FLASH_NOTES [V] | V | yes |
| Landing quickstart uses undefined $KEY / elides steps | `docs/index.html:140-144` (agent B) | V | yes |
| Feed trio: only curl shipped | `README.md:12,20,45-47,54`; no yaml in tree [V] | V | yes |
| Moods/kinds/holds/temps hardcoded; env knobs = lock/events/key/router-sock/rpc-timeout/upload-lock/port (no behavioral knobs) | `frames.py:119-131`, `moods.py:10-17`, `engine.py:30-38`, `webhook.py:120-121`, `bridge_client.py:28-30`, `upload.sh:9,21` [V] | V | yes |
| CLI lacks status/feed | `cli.py:31-39` [V] | V | yes |
| README "19 host-side tests" stale (28 actual) | `README.md:88` [V]; collect run [V] | V | yes |
| Shot list exists; zero media assets | `README.md:91-96`; find docs/ [V] | V | yes |
| Muse registration manual-only | `COMMANDS.md:20-54`, `familiar_specs.py` (agent C) | V | yes |
| MUSE_SESSION_ID documented but unused | `COMMANDS.md:65` vs engine.py grep (agent C) | V | yes |
| Contract test skips by default (MUSE_SDK_LINUX_DIR) — Muse-spec oracle dark | `tests/test_contract.py:14-16` [V] | V | yes |
| Narrator timeout 10 s (trail's 100 s stale) | `engine.py:88` [V] | V | no |
| cli.py + Narrator untested | grep zero refs [V] | V | yes |
| Webhook _STATE mutated unsynchronized across handler threads | `webhook.py:24-34` [V] | V | yes |
| Already fixed at HEAD: key-error text, frames._offset_rows | `webhook.py:123`, grep [V] | V | no |
| Narrator sync limitation | IMPLEMENTATION_VALIDATION.md:125-128 | R | no |
| Test residuals (chunk pin, LOCK_PATH, idle cross-pin, 200 arm) | TEST_VALIDATION.md:219-233 | R | no |
| Kill-test oracle weaknesses | IMPLEMENTATION_VALIDATION.md:116-120,201-204 | R | no |
| Pairing user-gate open | HANDOFF_LEDGER.md:12-13 | R | no |
| Suite 27p+1s / 28 collected at HEAD | run this session [V] | V | yes |
| test_landing pins formatting only (no regen parity) | `tests/test_landing.py:1-50` [V] | V | yes |
| msgpack-absent module skip | `tests/test_engine.py:19` [V] | V | yes |
| Gate manual-only (no hook/CI) | `.git/hooks/` samples only [V] | V | yes |
| FAMILIAR_LAN README residue (prior doc) | grep: absent today — already fixed | V | no |
| Sibling features (TTS, OTA, install.sh, env config, AGENTS.md, persistence, GH Action, STLs, App Lab, dashboard) | web agents' cited repos (Sources below) | R | no |

## Architecture Insights

- Mirrored patterns and their applicability: the repo's own conventions a
  feature-completion should follow — systemd hook scripts instead of inline
  Exec shell (units/*.sh, because systemd expands `$` itself); flock
  single-writer (upload.sh/engine); lazy-import msgpack with clean skip
  (bridge_client/test_engine); spec-shaped Muse commands
  (familiar_specs.py) tested by contract (test_contract.py); generated
  landing from source-of-truth art (make_landing imports frames.py).
  Each is tested (test_engine/test_contract/test_landing/test_meta
  respectively) and applies under the same conditions (user-unit systemd,
  optional msgpack, SDK executor schema).
- The landing page is the only "simulator" today; sibling projects ship
  full simulators — the regen coupling (frames.py → index.html) is the
  natural seam any simulator/config feature must preserve.

## Historical Context (from thoughts/)

- The 2026-10-04 plan deliberately scoped OUT: GitHub App integration,
  color matrix, per-frame RPC, posting by us (PLAN.md:18) — still matches
  code. Deferred to human gates: pixel assertion, pairing, release video
  (PLAN.md:41,87; HANDOFF_LEDGER:13) — still open.
- IMPLEMENTATION_VALIDATION's README `FAMILIAR_LAN` false promise
  (:109-111) no longer matches the README — fixed at release, no action.
- Waived PLAN drift items (argv hedge, license wording) remain waived;
  cosmetic only.
- Landing page was overhauled AFTER release by commits 110ee29 + 2cc19c3
  (banded sections, numbered headers, split controls, OG rebuild) —
  research treats current HEAD as truth; the overhaul added
  tests/test_landing.py but not regen parity.

## Coverage & Open Questions

- Searched: full tree, README/landing/COMMANDS verbatim steps, git
  history/reflog, tags/releases/repo metadata via gh, thoughts/ trail
  (all six plan artifacts + prior research), sibling projects via web.
- Bounded: sibling parity is web-sourced [R] and applicability-judged, not
  audited repo-by-repo; board-side facts (kill-test, flash, pairing state)
  are cited from trail/history, not re-run this session; the audit is
  sampled (medium profile, ≤2 rounds — round 1's findings were fixed
  in-place; no round 2 needed since every fix was a doc correction
  verified against code); `familiar/cli.py` and the engine `Narrator` are
  untested seams (recorded as a gap, not re-tested here); the engine unit's
  `uv run --with msgpack` resolves at every service start — cold-offline
  first-boot behavior unexamined (uv cache/network dependency, unexamined).
- Unconfirmed/unknown: whether the user wants sibling-parity features
  (TTS, persistence, personas) in scope now or later — plan must decide or
  carry forward; Muse official X handle (social concern, not repo);
  Arduino App Lab distribution feasibility for a Zephyr-core sketch
  (research found no channel — needs a decision if attempted).
- Out-of-repo fact (affects artifacts outside this repo): the social pack
  claims "repo topics already set" — verified FALSE (topics [] on GitHub);
  topics/homepage are unset as of this research.

Sources (sibling baseline): github.com/wupsbr/waveshare-muse-gadget-sdk,
github.com/vocino/muse-arr, github.com/facebookincubator/muse-gadget-sdk,
github.com/samyeei/Muse-charm-mosaico, github.com/cifertech/TamaFi,
github.com/socquique/TamaPoke, github.com/moonbench/catode32,
github.com/MaliosDark/Sablina-Tamagotchi-ESP32,
github.com/todbot/blink1,
github.com/t04glovern/github-actions-aws-iot-build-status-light,
github.com/blattmann/ai-status-light, docs.arduino.cc/hardware/uno-q/,
github.com/kartben/zephyr_unoq_demo.
