import os
import sys
import time
from contextlib import contextmanager

import pytest

from orchestrator.core.orchestrator import Orchestrator
from orchestrator.workflows.workflows import run_feature_add


@contextmanager
def _chdir(path: str):
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


def test_end_to_end_minimal(tmp_path, monkeypatch):
    # Deterministic env
    monkeypatch.setenv("PYTHONHASHSEED", "0")
    monkeypatch.setenv("TZ", "UTC")
    monkeypatch.setenv("LC_ALL", "C.UTF-8")
    monkeypatch.setenv("LANG", "C.UTF-8")
    # Use test mode so ContextStore falls back to a null backend without pyvesper
    monkeypatch.setenv("VLTAIR_TEST_MODE", "1")
    if hasattr(time, "tzset"):
        time.tzset()

    # Create minimal package structure in a temp repo
    pkg_dir = tmp_path / "pkg"
    tests_dir = tmp_path / "tests"
    pkg_dir.mkdir()
    tests_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("__all__ = []\n", encoding="utf-8")

    # Ensure child pytest can import the package by propagating PYTHONPATH via sandbox
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))

    with _chdir(str(tmp_path)):
        orc = Orchestrator()
        goal = "Implement function add(a, b) that returns a + b"
        target_file = "pkg/mod.py"
        res = run_feature_add(orc, goal, file=target_file)

    assert res.get("ok") is True
    ts = res.get("test_summary", {})
    # Minimal assertion: workflow reached test execution and passed
    assert ts.get("status") == "pass"
    steps = [s.get("name") for s in res.get("steps", [])]
    assert "codegen" in steps and "testgen" in steps and "testexec" in steps

