"""Opt-in test startup for Windows restricted-token temporary-directory ACLs."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


if os.name == "nt" and os.environ.get("TRPG_TEST_TEMP_INHERIT") == "1":
    _root = Path(__file__).resolve().parents[3]
    _scratch = _root / "eval/reports/046-test-temp"
    _scratch.mkdir(exist_ok=True)
    tempfile.tempdir = str(_scratch)
    _mkdir = os.mkdir

    def _inherited_mkdir(path, mode=0o777, *, dir_fd=None):
        # Python 3.13's 0700 creates a DACL excluding the current restricted token.
        # Use ordinary parent inheritance for new directories inside this checkout.
        # Existing ACLs and paths outside this checkout are never changed.
        if mode == 0o700 and Path(path).resolve().is_relative_to(_root):
            mode = 0o777
        return _mkdir(path, mode, dir_fd=dir_fd)

    os.mkdir = _inherited_mkdir
