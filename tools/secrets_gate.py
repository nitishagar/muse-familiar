#!/usr/bin/env python3
"""Secrets gate — refuses to let credentials into a pushed repo.

Tier (a) assignment scan over code/config files only (never markdown, so this
gate's own documentation cannot self-match): flags variables whose name
contains PASSWORD / TOKEN / SECRET / PASSKEY assigned a non-empty quoted
value.

Tier (b) literal scan over every file: `mgst_` SDK-token shapes, plus any
extra literal supplied at runtime via the SECRETS_GATE_EXTRA env var (e.g.
your WiFi SSID) — the gate itself stores nothing.

Scans the git index (everything staged/tracked — exactly what a push could
carry; gitignored device backups are deliberately excluded) AND every blob in
git history. Exit 0 clean, 1 dirty.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

CODE_EXTS = {".py", ".json", ".yaml", ".yml", ".toml", ".sh", ".cfg", ".ini"}
CODE_NAMES = lambda p: p.suffix.lower() in CODE_EXTS or p.name.startswith(".env")

ASSIGN_RE = re.compile(
    r"(?i)\b([A-Z0-9_]*(?:PASSWORD|TOKEN|SECRET|PASSKEY)[A-Z0-9_]*)\s*=\s*[\"'][^\"']+[\"']"
)
TOKEN_RE = re.compile(r"mgst_[A-Za-z0-9_-]{8,}")

# Reviewed allowlist: one regex per line, matched against finding TEXT
# (label + description) — each entry documents a known-synthetic pattern.
ALLOWLIST_FILE = ".secrets_allowlist"


def load_allowlist() -> list[re.Pattern]:
    path = REPO / ALLOWLIST_FILE
    if not path.is_file():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(re.compile(line))
    return out


def git_blobs() -> list[tuple[str, bytes]]:
    """(blob-id, content) for every blob in the object database — including
    unreferenced ones, so a 'removed' secret commit still trips the gate."""
    listing = subprocess.run(
        ["git", "cat-file", "--batch-all-objects", "--batch-check",
         "--unordered"],
        cwd=REPO, capture_output=True, text=True, errors="replace", check=True,
    ).stdout
    blob_ids = [line.split()[0] for line in listing.splitlines()
                if len(line.split()) >= 2 and line.split()[1] == "blob"]
    out = []
    for bid in blob_ids:
        content = subprocess.run(
            ["git", "cat-file", "blob", bid],
            cwd=REPO, capture_output=True, check=True,
        ).stdout
        out.append((bid, content))
    return out


def scan_text(label: str, text: str, is_code: bool,
              extra_literal: str | None, findings: list[str],
              collect=None) -> None:
    def report(finding: str) -> None:
        if collect is None:
            findings.append(finding)
        else:
            collect(finding)

    if is_code:
        for m in ASSIGN_RE.finditer(text):
            # preview keeps the quotes and is long enough (24) that every
            # allowlisted synthetic value appears in full in the finding text
            report(f"{label}: assignment to {m.group(1)!r} with a quoted "
                   f"value: {m.group(0).split('=', 1)[1].strip()[:24]!r}")
    for m in TOKEN_RE.finditer(text):
        report(f"{label}: possible Muse SDK token {m.group(0)[:12]}…")
    if extra_literal and extra_literal in text:
        report(f"{label}: contains the runtime-supplied literal")


def git_index_paths() -> list[Path]:
    """Everything staged or tracked — precisely what a push could carry."""
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout.split("\n")
    return [REPO / p for p in out if p.strip()]


def main() -> int:
    extra = os.environ.get("SECRETS_GATE_EXTRA") or None
    allowlist = load_allowlist()
    findings: list[str] = []

    def collect(finding: str) -> None:
        if not any(p.search(finding) for p in allowlist):
            findings.append(finding)

    for path in git_index_paths():
        if not path.is_file():
            continue
        rel = str(path.relative_to(REPO))
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        scan_text(rel, text, CODE_NAMES(path), extra, findings, collect)

    for bid, content in git_blobs():
        try:
            text = content.decode(errors="replace")
        except Exception:
            continue
        # history blobs lack filenames; treat as code for the assignment tier —
        # a real credential assignment in any blob is worth flagging.
        scan_text(f"history:{bid[:12]}", text, True, extra, findings, collect)

    if findings:
        print("SECRETS GATE: DIRTY")
        for f in findings:
            print(f"  - {f}")
        return 1
    print("SECRETS GATE: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
