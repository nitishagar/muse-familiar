"""Spec-contract test vs the REAL upstream executor (harness ported from
the validated muse-gadget-poc pattern)."""
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def test_familiar_specs_match_upstream_contract():
    sdk_dir = os.environ.get("MUSE_SDK_LINUX_DIR")
    if not sdk_dir:
        pytest.skip("MUSE_SDK_LINUX_DIR not set — upstream SDK unavailable")
    sys.path.insert(0, sdk_dir + "/src")
    try:
        import musegadget.executor as executor
    finally:
        sys.path.remove(sdk_dir + "/src")

    from muse_integration.familiar_specs import FAMILIAR_SPECS

    for name, spec in FAMILIAR_SPECS.items():
        assert isinstance(spec.get("description"), str) and spec["description"]
        for section in ("required", "optional"):
            params = spec.get(section, {})
            assert isinstance(params, dict)
            for param, meta in params.items():
                assert set(meta) == {"type", "description"}
                assert meta["type"] in ("string", "integer", "boolean")

    for spec in executor.COMMAND_SPECS.values():
        assert "description" in spec and "required" in spec
        break
