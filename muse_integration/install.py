#!/usr/bin/env python3
"""Register the familiar.* commands in the board's Muse gadget SDK.

    sudo python3 muse_integration/install.py [--check] [--force]
         [--venv /opt/musegadget/venv] [--repo DIR] [--no-restart]
    sudo python3 muse_integration/install.py --remove

What it does: finds musegadget/executor.py inside the SDK venv, takes a
timestamped backup, appends a 3-line guarded hook that imports THIS repo's
familiar_specs.register() (single source — no spec text is copied into the
venv), compiles the patched source, then atomically replaces the file and
restarts the musegadget service. A missing/unreadable repo degrades to
"familiar commands absent" (the hook swallows its own failure) — the SDK
keeps working either way. --remove restores the OLDEST backup (the true
pre-familiar original) and deletes newer ones.
"""

from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SENTINEL = "# --- muse-familiar hook (install.py --remove reverses) ---"
BACKUP_GLOB = "executor.py.familiar-bak-*"


def find_executor(venv: str) -> str:
    matches = sorted(glob.glob(
        os.path.join(venv, "lib", "python3*", "site-packages",
                     "musegadget", "executor.py")))
    if not matches:
        raise SystemExit(f"no musegadget/executor.py under {venv}")
    if len(matches) > 1:
        raise SystemExit(f"ambiguous executor.py: {matches}")
    return matches[0]


def hook_source(repo: str) -> str:
    return f'''

{SENTINEL}
try:
    import sys as _sys
    _sys.path.append({repo!r})   # append: repo code must not shadow stdlib
    from muse_integration.familiar_specs import register as _familiar_register
    _familiar_register(globals(), {repo!r})
except Exception:  # the gadget service must survive a missing repo
    import logging as _logging
    _logging.getLogger(__name__).exception("familiar hook failed")
'''


def backups(executor: str) -> list[str]:
    return sorted(glob.glob(os.path.join(os.path.dirname(executor),
                                         BACKUP_GLOB)))


def verify_registration(venv: str, executor: str) -> list[str]:
    """Import the patched executor the way the service does — as a package,
    under the venv's python when one exists — and return the familiar.*
    specs that registered. Fresh-file exec is NOT a valid oracle: the real
    executor reads `from musegadget import __version__` at module level
    and decorates with @dataclass, which both need package context.
    """
    site_packages = os.path.dirname(os.path.dirname(executor))
    code = ("import sys; sys.path.insert(0, %r); "
            "import musegadget.executor as e; "
            "print(' '.join(sorted(k for k in e.COMMAND_SPECS "
            "if k.startswith('familiar.'))))" % site_packages)
    venv_python = os.path.join(venv, "bin", "python")
    if os.path.isfile(venv_python) and os.access(venv_python, os.X_OK):
        argv = [venv_python, "-c", code]
    else:
        argv = [sys.executable, "-c", code]
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=120,
                          cwd="/")   # cwd-neutral: only the inserted paths resolve
    if proc.returncode != 0:
        raise RuntimeError(f"verification import failed: "
                           f"{proc.stderr.strip()[:400]}")
    return proc.stdout.split()


def restart_service(dry: bool = False) -> None:
    if dry:
        print("install.py: would: systemctl restart musegadget")
        return
    subprocess.run(["systemctl", "restart", "musegadget"], check=False)
    print("install.py: restarted musegadget")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="dry run")
    ap.add_argument("--force", action="store_true",
                    help="re-patch even if the hook is present")
    ap.add_argument("--venv", default="/opt/musegadget/venv")
    ap.add_argument("--repo", default=REPO,
                    help="repo root the hook imports from (default: auto)")
    ap.add_argument("--no-restart", action="store_true")
    ap.add_argument("--remove", action="store_true",
                    help="restore the original executor and restart")
    ns = ap.parse_args(argv)

    executor = find_executor(ns.venv)
    source = open(executor).read()
    patched = SENTINEL in source

    if ns.remove:
        baks = backups(executor)
        if not patched and not baks:
            print("install.py: nothing to remove (no hook, no backups)")
            return 0
        if not baks:
            raise SystemExit("hook present but no backup found — refusing; "
                             "remove manually or reinstall the SDK")
        original = open(baks[0], "rb").read()          # oldest = pre-familiar
        if ns.check:
            print(f"install.py: would: restore {baks[0]} -> {executor} "
                  f"and delete {len(baks)} backup(s)")
            return 0
        tmp = executor + ".familiar-tmp"
        try:
            with open(tmp, "wb") as f:
                f.write(original)
            compile(open(tmp).read(), executor, "exec")  # verify before swap
            os.replace(tmp, executor)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        for bak in baks:                 # restore consumed them all
            os.unlink(bak)
        print(f"install.py: restored original executor from {baks[0]}")
        if not ns.no_restart:
            restart_service()
        return 0

    if patched and not ns.force:
        print(f"install.py: hook already present in {executor} (use --force "
              "to re-patch, --remove to undo)")
        return 0

    action = "re-patch" if patched else "patch"
    if ns.check:
        print(f"install.py: would: {action} {executor} (backup + guarded "
              f"import of {ns.repo}/muse_integration/familiar_specs.py), "
              f"restart musegadget")
        return 0

    backup = f"{executor}.familiar-bak-{time.strftime('%Y%m%dT%H%M%S')}"
    n = 1
    while os.path.exists(backup):   # two installs in one second must not
        backup = (f"{executor}.familiar-bak-"
                  f"{time.strftime('%Y%m%dT%H%M%S')}-{n}")  # clobber history
        n += 1
    shutil.copy2(executor, backup)
    print(f"install.py: backup -> {backup}")

    new_source = source + hook_source(os.path.abspath(ns.repo))
    tmp = executor + ".familiar-tmp"
    try:
        compile(new_source, executor, "exec")  # never swap in a broken file
        with open(tmp, "w") as f:
            f.write(new_source)
        os.replace(tmp, executor)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        shutil.copy2(backup, executor)  # put the known-good file back
        raise
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    try:
        registered = verify_registration(ns.venv, executor)
    except Exception as exc:
        shutil.copy2(backup, executor)
        raise SystemExit(f"patched executor failed verification ({exc!r}) "
                         "— backup restored")
    if not registered:
        shutil.copy2(backup, executor)
        raise SystemExit("patched executor loaded but familiar.* specs "
                         "missing — backup restored; inspect the hook")
    print(f"install.py: verified registration: {' '.join(registered)}")

    if not ns.no_restart:
        restart_service()
    print("install.py: done — ask Muse: 'How is the Familiar doing?'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
