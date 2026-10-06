"""install.py against a STUB executor in tmp_path — never a live venv.

The hook imports the REAL muse_integration/familiar_specs.py from this
repo, so these tests prove the single-source registration end to end:
patched module loads, specs merge, dispatch allowlists, backups restore.
"""
import importlib.util
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent

STUB_EXECUTOR = '''
from dataclasses import dataclass

from musegadget import __version__


@dataclass(frozen=True)
class Account:
    name: str


COMMAND_SPECS = {"system.run": {"description": "stub", "required": {}, "optional": {}}}


def ok(payload):
    return {"ok": True, "payload": payload}


def error(message):
    return {"ok": False, "error": message}


class Executor:
    def __init__(self):
        self.commands = []

    def system_run(self, params, timeout_ms):
        # positional timeout_ms, like the real SDK signature
        self.commands.append(params["command"])
        return ok({"exit_code": 0})

    def run(self, command, params, timeout_ms=None):
        return error(f"unsupported command: {command}")
'''


def make_stub_venv(tmp_path):
    venv = tmp_path / "venv"
    pkg = venv / "lib" / "python3.12" / "site-packages" / "musegadget"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text('__version__ = "9.9-stub"\n')
    executor = pkg / "executor.py"
    executor.write_text(STUB_EXECUTOR)
    return venv, executor


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module          # @dataclass looks the module up here
    spec.loader.exec_module(module)
    return module


def run_install(*argv):
    spec = importlib.util.spec_from_file_location(
        "muse_install", REPO / "muse_integration" / "install.py")
    install = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(install)
    return install.main(list(argv))


def test_install_patches_registers_and_verifies(tmp_path, capsys):
    venv, executor = make_stub_venv(tmp_path)
    site_packages = str(executor.parent.parent)
    sys.path.insert(0, site_packages)   # stub's `from musegadget import …`
    try:
        original = executor.read_bytes()

        rc = run_install("--venv", str(venv), "--repo", str(REPO),
                         "--no-restart")
        assert rc == 0, capsys.readouterr().out
        out = capsys.readouterr().out
        assert ("verified registration: "
                "familiar.feed familiar.show familiar.status") in out
        baks = sorted(venv.glob("**/executor.py.familiar-bak-*"))
        assert len(baks) == 1 and baks[0].read_bytes() == original

        # the patched module actually dispatches with allowlists
        module = load_module(executor, "executor_patched")
        assert "familiar.status" in module.COMMAND_SPECS
        ex = module.Executor()
        assert ex.run("familiar.show", {"mood": "happy"})["ok"] is True
        assert "show happy" in ex.commands[-1]
        assert ex.run("familiar.show", {"mood": "rm -rf /"})["ok"] is False
        assert ex.run("familiar.feed", {"kind": "x; reboot"})["ok"] is False
        assert ex.run("familiar.feed", {"kind": "ci_green"})["ok"] is True
        # original path preserved (stub returns unsupported for system.run)
        assert ex.run("system.run", {"command": "true"})["ok"] is False
    finally:
        sys.path.remove(site_packages)


def test_install_is_idempotent(tmp_path, capsys):
    venv, executor = make_stub_venv(tmp_path)
    run_install("--venv", str(venv), "--repo", str(REPO), "--no-restart")
    first = executor.read_bytes()
    rc = run_install("--venv", str(venv), "--repo", str(REPO), "--no-restart")
    assert rc == 0
    assert executor.read_bytes() == first            # untouched
    assert "already present" in capsys.readouterr().out
    assert len(sorted(venv.glob("**/executor.py.familiar-bak-*"))) == 1


def test_remove_restores_original_bytes_after_force(tmp_path, capsys):
    venv, executor = make_stub_venv(tmp_path)
    original = executor.read_bytes()
    run_install("--venv", str(venv), "--repo", str(REPO), "--no-restart")
    run_install("--venv", str(venv), "--repo", str(REPO), "--no-restart", "--force")
    assert len(sorted(venv.glob("**/executor.py.familiar-bak-*"))) == 2

    rc = run_install("--venv", str(venv), "--remove", "--no-restart")
    assert rc == 0
    assert executor.read_bytes() == original          # OLDEST backup wins
    assert sorted(venv.glob("**/executor.py.familiar-bak-*")) == []
    sys.path.insert(0, str(executor.parent.parent))
    try:
        module = load_module(executor, "executor_restored")
        assert "familiar.status" not in module.COMMAND_SPECS
    finally:
        sys.path.remove(str(executor.parent.parent))
    # no temp residue anywhere
    assert sorted(venv.glob("**/*familiar-tmp*")) == []


def test_crash_before_replace_leaves_original(tmp_path, monkeypatch):
    venv, executor = make_stub_venv(tmp_path)
    original = executor.read_bytes()
    spec = importlib.util.spec_from_file_location(
        "muse_install", REPO / "muse_integration" / "install.py")
    install = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(install)

    real_replace = install.os.replace
    def boom(*a, **k):
        raise RuntimeError("simulated crash mid-install")
    monkeypatch.setattr(install.os, "replace", boom)
    try:
        install.main(["--venv", str(venv), "--repo", str(REPO), "--no-restart"])
        raised = False
    except RuntimeError:
        raised = True
    assert raised
    monkeypatch.setattr(install.os, "replace", real_replace)
    assert executor.read_bytes() == original          # os.replace never ran
    # the exception path restored the known-good file from backup
    sys.path.insert(0, str(executor.parent.parent))
    try:
        module = load_module(executor, "executor_crashrec")
        assert "familiar.status" not in module.COMMAND_SPECS
    finally:
        sys.path.remove(str(executor.parent.parent))


def test_verification_failure_restores_original(tmp_path):
    # A python that cannot import muse_integration (clean env, cwd=/) makes
    # the hook degrade to no-registration: install.py must refuse AND put
    # the original back. (In-process run_install cannot reproduce this —
    # the repo's editable install resolves the import under the venv python.)
    import subprocess
    venv, executor = make_stub_venv(tmp_path)
    original = executor.read_bytes()
    r = subprocess.run(
        ["/usr/bin/env", "python3",
         str(REPO / "muse_integration" / "install.py"),
         "--venv", str(venv), "--repo", "/nonexistent-repo", "--no-restart"],
        capture_output=True, text=True, cwd="/",
        env={"HOME": "/tmp", "PATH": "/usr/local/bin:/usr/bin:/bin"})
    assert r.returncode != 0
    assert "backup restored" in (r.stdout + r.stderr)
    assert executor.read_bytes() == original
    assert sorted(venv.glob("**/executor.py.familiar-bak-*"))  # kept for audit
    assert sorted(venv.glob("**/*familiar-tmp*")) == []
