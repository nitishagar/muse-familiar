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
