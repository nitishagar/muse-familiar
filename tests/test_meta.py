"""Phase 1 scaffold tests: layout present, client importable, gate clean."""
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent


def test_layout_present():
    for rel in ("familiar/bridge_client.py", "familiar/__init__.py",
                "firmware/FramePlayer/FramePlayer.ino", "firmware/upload.sh",
                "pyproject.toml", "tools/secrets_gate.py"):
        assert (REPO / rel).is_file(), rel


def test_bridge_client_imports_without_msgpack():
    sys.path.insert(0, str(REPO))
    from familiar import bridge_client  # noqa: F401  (msgpack is lazy)
    assert bridge_client.DEFAULT_SOCKET.endswith("arduino-router.sock")


def test_no_token_anywhere():
    out = subprocess.run(["git", "grep", "-lE", r"mgst_[A-Za-z0-9_-]{8,}"],
                         cwd=REPO, capture_output=True, text=True)
    assert out.stdout.strip() == "", f"token-shaped literal in repo:\n{out.stdout}"


def test_no_router_socket_widening_in_executable_code():
    out = subprocess.run(
        ["grep", "-rn", "-E", r"chmod.*arduino-router|chown.*arduino-router",
         "familiar/", "firmware/upload.sh"],
        capture_output=True, text=True, cwd=REPO)
    assert out.stdout.strip() == ""


def test_sketch_clamps_present():
    # The MCU-side safety caps must stay in the sketch (spec inv 2): fps
    # floor via MIN_PERIOD_MS, frame cap, idle timeout, 3-bit depth.
    ino = (REPO / "firmware" / "FramePlayer" / "FramePlayer.ino").read_text()
    for anchor in ("MIN_PERIOD_MS = 250", "MAX_FRAMES  = 64",
                   "IDLE_TIMEOUT_MS = 30000", "setGrayscaleBits(3)"):
        assert anchor in ino, f"sketch clamp anchor missing: {anchor!r}"


def test_no_coauthor_trailers_in_log():
    # Commit hygiene invariant: no attribution trailers anywhere in history
    # (mirrors the CI step; needs a full clone to mean anything).
    out = subprocess.run(
        ["git", "log", "--all", "--grep=Co-Authored-By", "--format=%H"],
        cwd=REPO, capture_output=True, text=True)
    assert out.stdout.strip() == "", f"co-author trailers in history:\n{out.stdout}"


def test_docs_no_dangling_references():
    # Docs are copy-paste-runnable (spec inv 11): no references to paths the
    # repo doesn't ship, no dangling unit-install comment, and the landing
    # never uses an undefined shell variable (README defines KEY inline).
    readme = (REPO / "README.md").read_text()
    landing = (REPO / "docs" / "index.html").read_text()
    for text, name in ((readme, "README.md"), (landing, "docs/index.html")):
        for banned in ("sdk-linux/", "after installing the unit"):
            assert banned not in text, f"{name} references {banned!r}"
    assert "$KEY" not in landing, "landing uses $KEY without defining it"
