# Security Review — muse-familiar completion diff (19e3234..HEAD)

Reviewer: security-reviewer agent (fresh; report delivered in-message —
persisted verbatim by the coordinator). Scope: `git diff 19e3234..HEAD`.

## Critical / High / Medium
None.

## Low (acknowledged; 1,2,3,4,5,6,7 addressed in commit "Security
hardening" — see below; 8 accepted as theoretical)

1. Root-context import of user-writable repo code during install
   verification (install.py verify_registration) — equivalent-privilege
   to what root volunteered (sudo pip install <dir> pattern); trust
   boundary now documented in COMMANDS.md.
2. Webhook key in argv via $(cat key) in the registered feed command —
   FIXED: familiar.feed now routes through `familiar.cli feed` (key stays
   out of argv; CLI re-validates kind).
3. Unvalidated path interpolation into systemd drop-in — FIXED:
   install.sh rejects whitespace/newline in REPO/UV_BIN.
4. Cleartext key on LAN in --lan mode — documented tradeoff, note added
   to examples/README.md (Tailscale/HTTPS suggestion).
5. Third-party actions pinned by tag — FIXED: pinned to commit SHAs
   (checkout 11d5960a…, setup-uv d4b2f3b6…).
6. Repo root PREPENDED to service sys.path — FIXED: hook appends instead
   (repo code cannot shadow stdlib).
7. familiar handlers dropped the timeout — FIXED: timeout_ms 120000
   passed through to system_run.
8. Fixed tmp name in root-owned dir — theoretical only (requires write
   access to root-owned site-packages); accepted.

## Verified clean
{repo!r} repr breakout: none (repr round-trips; compile() + verification
fail closed). _valid_kind bypass: none (isalnum admits no shell/JSON
metachars; unknown kinds ignored server-side). No SSRF (hardcoded
localhost/loopback). CLI key never printed/logged/argv'd; no tracebacks
on 401/429/conn. install.sh key: umask 177 → 0600, 192-bit entropy. CI:
no secrets in PR path, permissions contents:read, log injection-free
co-author step. Examples: key header-only, GitHub masks secrets in logs;
HA uses !secret. Tests: fake keys only; minimal-env subprocess.
Whole-diff sweep: no credential-shaped literals, no eval/exec/pickle/
shell=True additions, no .env files, glob discovery can't traverse.

VERDICT: PASS
