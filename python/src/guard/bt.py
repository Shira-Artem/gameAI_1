"""Минимальное дерево поведения: Sequence / Selector / Condition / Action."""

from enum import Enum
from typing import Callable


class Status(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"


class Node:
    def tick(self, bb: dict) -> Status:  # bb — blackboard
        raise NotImplementedError


class Condition(Node):
    def __init__(self, fn: Callable[[dict], bool]):
        self.fn = fn

    def tick(self, bb):
        return Status.SUCCESS if self.fn(bb) else Status.FAILURE


class Action(Node):
    def __init__(self, fn: Callable[[dict], Status]):
        self.fn = fn

    def tick(self, bb):
        return self.fn(bb)


class Sequence(Node):
    def __init__(self, *children: Node):
        self.children = children

    def tick(self, bb):
        for c in self.children:
            s = c.tick(bb)
            if s != Status.SUCCESS:
                return s
        return Status.SUCCESS


class Selector(Node):
    def __init__(self, *children: Node):
        self.children = children

    def tick(self, bb):
        for c in self.children:
            s = c.tick(bb)
            if s != Status.FAILURE:
                return s
        return Status.FAILURE


def build_guard_tree() -> Node:
    """Приоритет: атака, тревога, преследование, слух, поиск, патруль."""
    return Selector(
        Sequence(Condition(lambda bb: bb.get("see_player") and bb.get("in_attack_range")),
                 Action(lambda bb: bb.update(action="attack") or Status.RUNNING)),
        Sequence(Condition(lambda bb: bb.get("alert_phase")),
                 Action(lambda bb: bb.update(action="alert") or Status.RUNNING)),
        Sequence(Condition(lambda bb: bb.get("see_player")),
                 Action(lambda bb: bb.update(action="chase") or Status.RUNNING)),
        Sequence(Condition(lambda bb: bb.get("hear_noise")),
                 Action(lambda bb: bb.update(action="alert") or Status.RUNNING)),
        Sequence(Condition(lambda bb: bb.get("searching")),
                 Action(lambda bb: bb.update(action="search") or Status.RUNNING)),
        Action(lambda bb: bb.update(action="patrol") or Status.RUNNING),
    )
