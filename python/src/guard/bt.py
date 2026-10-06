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
    """Приоритет: незавершённая тревога, атака, преследование, поиск, слух, патруль."""
    return Selector(
        Sequence(Condition(lambda bb: bb.get("alert_phase")),
                 Action(lambda bb: bb.update(action="alert") or Status.RUNNING)),
        Sequence(Condition(lambda bb: bb.get("see_player") and bb.get("in_attack_range")),
                 Action(lambda bb: bb.update(action="attack") or Status.RUNNING)),
        Sequence(Condition(lambda bb: bb.get("see_player")),
                 Action(lambda bb: bb.update(action="chase") or Status.RUNNING)),
        Sequence(Condition(lambda bb: bb.get("searching")),
                 Action(lambda bb: bb.update(action="search") or Status.RUNNING)),
        Sequence(Condition(lambda bb: bb.get("hear_noise")),
                 Action(lambda bb: bb.update(action="alert") or Status.RUNNING)),
        Action(lambda bb: bb.update(action="patrol") or Status.RUNNING),
    )


def update_guard_tree(tree: Node, bb: dict, dt: float, alert_duration=1.0, search_duration=10.0) -> str:
    """Подготовить таймеры blackboard, затем выбрать действие существующим деревом."""
    previous = bb.get("action", "patrol")
    visible = bb.get("see_player")
    bb["alert_time"] = max(0.0, bb.get("alert_time", 0.0) - dt)
    bb["search_time"] = max(0.0, bb.get("search_time", 0.0) - dt)
    if previous == "patrol" and (visible or bb.get("hear_noise")):
        bb["alert_time"] = alert_duration
    elif previous == "alert" and bb["alert_time"] <= 0 and not visible:
        bb["search_time"] = search_duration
    elif previous in ("chase", "attack") and not visible:
        bb["search_time"] = search_duration
    if visible:
        bb["search_time"] = 0.0
    bb.update(alert_phase=bb["alert_time"] > 0, searching=bb["search_time"] > 0)
    tree.tick(bb)
    if bb["action"] == "alert" and previous != "alert":
        bb["alert_time"] = alert_duration
    return bb["action"]
