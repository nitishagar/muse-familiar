"""install.sh --check harness: dry-run output assertions over a fake HOME.

--check is side-effect-free by contract, so these run the real script and
assert the plan it prints — including the no-change case, which pins the
restart-only-on-change invariant (a regressed unconditional restart shows
up here as a false 'restart' line).
"""
import os
import pathlib
import re
import subprocess

REPO = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "install.sh"


def run_check(fake_home: pathlib.Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, HOME=str(fake_home))
    return subprocess.run(["bash", str(SCRIPT), "--check", "--repo", str(REPO)],
                          capture_output=True, text=True, env=env, timeout=30)


def test_check_first_run_prints_exact_dropin(tmp_path):
    out = run_check(tmp_path)
    assert out.returncode == 0, out.stderr
    assert "READY" in out.stdout
    assert "exact drop-in content" in out.stdout
    # the reset-then-set pattern for every path-bearing directive
    for directive in ("ExecStartPre", "Environment", "ExecStart", "ExecStopPost"):
        assert re.search(rf"^\s*{directive}=$", out.stdout, re.M), directive
        assert re.search(rf"^\s*{directive}=\S", out.stdout, re.M), directive
    assert "restart" in out.stdout          # key + link + drop-in all pending


def test_check_noop_rerun_needs_no_restart(tmp_path):
    home = tmp_path
    first = run_check(home)
    assert first.returncode == 0

    # materialize the printed state: key, drop-in (exact content), unit link
    (home / ".config/familiar").mkdir(parents=True)
    (home / ".config/familiar/key").write_text("k\n")
    dropin_block = first.stdout.split("exact drop-in content")[1]
    content = "\n".join(line[4:] for line in dropin_block.splitlines()
                        if line.startswith("    ")) + "\n"
    dropin = home / ".config/systemd/user/familiar-engine.service.d/override.conf"
    dropin.parent.mkdir(parents=True)
    dropin.write_text(content)
    unit_link = home / ".config/systemd/user/familiar-engine.service"
    unit_link.symlink_to(REPO / "units/familiar-engine.service")

    again = run_check(home)
    assert again.returncode == 0, again.stderr
    assert "already current" in again.stdout
    assert "no restart needed" in again.stdout
    assert "generate" not in again.stdout
    # nothing was touched by the dry run
    assert dropin.read_text() == content
    assert unit_link.is_symlink()
