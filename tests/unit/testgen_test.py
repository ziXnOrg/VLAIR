from __future__ import annotations

import builtins
from typing import Any, Dict

from orchestrator.agents.test_gen import TestAgent
from orchestrator.schemas.validators import validate_agent_result, validate_agent_task


def test_testgen_generate_python_compiles(tmp_path) -> None:
    agent = TestAgent()
    task: Dict[str, Any] = {
        "type": "AgentTask",
        "id": "t1",
        "agent": "TestAgent",
        "payload": {"mode": "generate", "target": "sample_mod.py", "function": "foo"},
    }

    # Validate task payload shape
    validate_agent_task(task)

    res = agent.run(task, None)

    # Shape checks
    assert res["type"] == "AgentResult"
    assert res["parentId"] == "t1"
    assert res["agent"] == "TestAgent"
    doc = res["payload"]["delta"]["doc"]
    assert doc["path"] == "test_sample_mod.py"
    content = doc["content"]
    assert isinstance(content, str) and len(content) > 0

    # Validate result schema
    validate_agent_result(res)

    # Integration-lite: ensure it compiles as Python (do not exec to avoid imports)
    path = tmp_path / "test_sample_mod.py"
    path.write_text(content, encoding="utf-8")
    _ = builtins.compile(content, str(path), "exec")


def test_testgen_is_deterministic() -> None:
    agent = TestAgent()
    task: Dict[str, Any] = {
        "type": "AgentTask",
        "id": "t2",
        "agent": "TestAgent",
        "payload": {
            "mode": "generate",
            "target": "pkg/utils/sample.py",
            "function": "bar",
        },
    }
    res1 = agent.run(task, None)
    res2 = agent.run(task, None)
    assert (
        res1["payload"]["delta"]["doc"]["content"]
        == res2["payload"]["delta"]["doc"]["content"]
    )


def test_testgen_filename_and_header() -> None:
    agent = TestAgent()
    task: Dict[str, Any] = {
        "type": "AgentTask",
        "id": "t3",
        "agent": "TestAgent",
        "payload": {"mode": "generate", "target": "pkg/foo.py"},
    }
    res = agent.run(task, None)
    doc = res["payload"]["delta"]["doc"]
    assert doc["path"] == "test_foo.py"
    assert doc["content"].startswith("# generated:test:pkg.foo:")
