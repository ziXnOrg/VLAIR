from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set


@dataclass
class Node:
  id: str
  deps: Set[str] = field(default_factory=set)


class DAG:
  def __init__(self) -> None:
    self._nodes: Dict[str, Node] = {}

  def add_node(self, node_id: str, deps: List[str] | None = None) -> None:
    if node_id not in self._nodes:
      self._nodes[node_id] = Node(id=node_id)
    if deps:
      self._nodes[node_id].deps.update(deps)
      for d in deps:
        if d not in self._nodes:
          self._nodes[d] = Node(id=d)

  def mark_done(self, node_id: str) -> None:
    if node_id in self._nodes:
      del self._nodes[node_id]
      for n in self._nodes.values():
        n.deps.discard(node_id)

  def ready(self) -> List[str]:
    return [n.id for n in self._nodes.values() if not n.deps]
