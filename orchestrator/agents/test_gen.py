from __future__ import annotations

from typing import Any, Dict, Optional

from .base import Agent, AgentContext


class TestAgent(Agent):
    """Deterministic Test Generator.

    Inputs are limited to payload fields (no randomness, no wall-clock).
    Output is a stable test file skeleton targeting the given module/function.
    """

    def __init__(self) -> None:
        super().__init__("TestAgent")

    def _to_module_name(self, target: str) -> str:
        # Convert a path like "pkg/sub/module.py" to import name "pkg.sub.module"
        mod = target.replace("\\", ".").replace("/", ".")
        if mod.endswith(".py"):
            mod = mod[:-3]
        return mod

    def _test_filename(self, target: str) -> str:
        # Derive test filename as "test_<module>.py" based on the leaf module name
        leaf = target.split("/")[-1].split("\\")[-1]
        if leaf.endswith(".py"):
            leaf = leaf[:-3]
        return f"test_{leaf}.py"

    def _render_content(self, module_name: str, func: Optional[str]) -> str:
        header = f"# generated:test:{module_name}:{func or ''}\n"
        body_lines = [
            "import importlib",
            "import types",
            "",
            "def test_smoke_import():",
            f'    mod = importlib.import_module("{module_name}")',
            "    assert isinstance(mod, types.ModuleType)",
        ]
        if func:
            body_lines.extend(
                [
                    "",
                    f"def test_{func}_exists():",
                    f'    mod = importlib.import_module("{module_name}")',
                    f'    assert hasattr(mod, "{func}")',
                ]
            )
        return header + "\n".join(body_lines) + "\n"

    def run(
        self, task: Dict[str, Any], ctx: AgentContext | None = None
    ) -> Dict[str, Any]:
        payload = task.get("payload", {})
        target = str(payload.get("target", ""))
        function_any = payload.get("function")
        function = function_any if isinstance(function_any, str) else None

        # Deterministic content derived only from inputs
        module_name = self._to_module_name(target)
        path = self._test_filename(target)
        content = self._render_content(module_name, function)

        result: Dict[str, Any] = {
            "type": "AgentResult",
            "id": f"res-{task.get('id', '')}",
            "parentId": str(task.get("id", "")),
            "agent": self.name,
            "payload": {
                "delta": {
                    "doc": {
                        "path": path,
                        "content": content,
                    }
                }
            },
            "protocolVersion": 1,
        }
        return result
