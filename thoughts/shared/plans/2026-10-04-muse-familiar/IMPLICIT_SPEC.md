<!-- SIGNPOST | 1/5: SPEC | requirements only, no designs | Next: PLAN.md
     Pipeline: SPEC -> PLAN -> PLAN_VALIDATION -> implement+review -> tests+TEST_VALIDATION -> green -->

# Implicit Spec — muse-familiar

Seeded from `thoughts/shared/research/2026-10-04-muse-familiar-matrix.md` (audit-corrected). Requirements only.

## Invariants

1. **Token secrecy**: the SDK token exists only in the ticket conversation and the board's root-only `/var/lib/musegadget/sdk_token`. It appears in no file, commit, log, doc, or social artifact of any repo. Observable: secrets gate green (mgst_ tier) on muse-familiar AND muse-gadget-poc before any push/flip; `git grep` clean.
2. **Board safety, scoped**: the ONLY system-wide change is the Muse SDK install (explicitly user-approved in the ticket). All Familiar code = user units + `~/muse-familiar` dir + the MCU sketch; stock arduino-* services untouched; router socket permissions never modified. Observable: snapshot diff (system unit files, /etc/systemd, socket mode/owner) before/after each stage; uninstall path in README.
3. **MCU flash safety**: first upload records the pre-flash state and recovery notes (BOOTESL/EDL per docs); uploads only via the documented arduino-cli network flow; the deployed sketch keeps the Bridge responsive so re-upload stays possible. Observable: re-upload proven once after the Familiar sketch is live.
4. **No raw router passthrough to Muse**: Muse drives the Familiar only through our validated engine commands; nothing exposes router RPC to Muse. Observable: executable-code grep + review.
5. **Effects bounded, crash-safe, photosensitive-safe**: animations ≤ 4 fps, grayscale ≤ 7; engine stop resets matrix + LEDs (hook scripts); single-writer discipline via the existing flock (engine) and an engine pause before any upload. Observable: codec bounds in tests; kill-test; pause hook.
6. **Webhook hardened**: shared-key header (constant-time), payload ≤ 2 KiB, per-source rate cap with flood test, loopback bind by default. Observable: unit tests incl. flood/oversize/wrong-key.
7. **No-token demo mode**: every automated criterion passes with no Muse pairing (webhook + CLI + animations); pairing is a documented manual gate that lights up narration/commands. Observable: criteria executed pre-pairing.
8. **Spec-contract fidelity**: `familiar.*` command specs validate against the real upstream `COMMAND_SPECS` (import harness, observed with clone at least once per release). Observable: contract test.
9. **Release hygiene**: MIT LICENSE + NOTICE (SDK Apache-2.0; own bridge client written from the RPClite protocol — CC BY-SA tutorial NOT copied; Arduino docs referenced), README with quickstart + GIF shot list, SOCIAL.md pack tagging Muse + Arduino UNO Q, zero co-author trailers, repo private first → secrets-gated → public flip (user-approved by ticket).
10. **Bounding assumptions**: board at 192.168.0.134 (key auth; network-upload password = board Linux password, held out-of-band); user completes phone BLE pairing when they choose (implementation leaves pairing open + documents `sudo musegadget pair` reopen); demo webhook = curl/GitHub-style JSON; matrix is blue-mono 8×13; muse-gadget-poc stays private as the engineering trail.

## Intent open questions → closure checklist
- [x] Q1 (matrix drivable end-to-end) — critical-path facts verified in research; end-to-end PROOF is plan Milestone 1 (first thing built, before the engine).
- [x] Q2 (flash safety/backup) — recovery notes + re-upload proof (invariant 3).
- [x] Q3 (pre-pairing verification) — install state, pairing-open, engine demo, contract specs (invariant 7 + Phase criteria).
- [x] Q4 (release contents) — invariant 9 checklist + SOCIAL.md deliverable.
