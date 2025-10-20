from __future__ import annotations

from typing import Any, Dict


class Agent:
  name: str

  def __init__(self, name: str) -> None:
    self.name = name

  def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
    raise NotImplementedError


