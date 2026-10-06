"""Конечный автомат стражника для учебной pygame-сцены."""

from enum import Enum, auto


class State(Enum):
    PATROL = auto()
    ALERT = auto()
    CHASE = auto()
    ATTACK = auto()
    SEARCH = auto()
    RETURN = auto()


TRANSITIONS: dict[tuple[State, str], State] = {
    (State.PATROL, "see_player"): State.ALERT,
    (State.PATROL, "hear_noise"): State.ALERT,
    (State.ALERT, "confirm"): State.CHASE,
    (State.ALERT, "timeout"): State.PATROL,
    (State.ALERT, "investigate"): State.SEARCH,
    (State.CHASE, "in_range"): State.ATTACK,
    (State.CHASE, "lost"): State.SEARCH,
    (State.ATTACK, "out_of_range"): State.CHASE,
    (State.ATTACK, "lost"): State.SEARCH,
    (State.SEARCH, "see_player"): State.CHASE,
    (State.SEARCH, "timeout"): State.RETURN,
    (State.RETURN, "arrived"): State.PATROL,
}


class GuardFSM:
    def __init__(self) -> None:
        self.state = State.PATROL
        self.history: list[tuple[State, str, State]] = []

    def fire(self, trigger: str) -> bool:
        nxt = TRANSITIONS.get((self.state, trigger))
        if nxt is None:
            return False
        self.history.append((self.state, trigger, nxt))
        self.state = nxt
        return True

    def update(self, bb: dict, dt: float, alert_duration=1.0, search_duration=10.0) -> str:
        """Сенсоры и таймеры создают события; переходы по-прежнему выполняет fire."""
        visible, heard = bb.get("see_player"), bb.get("hear_noise")
        bb["alert_time"] = max(0.0, bb.get("alert_time", 0.0) - dt)
        if self.state == State.PATROL and (visible or heard):
            self.fire("see_player" if visible else "hear_noise")
            bb["alert_time"] = alert_duration
        elif self.state == State.ALERT and bb["alert_time"] <= 0:
            self.fire("confirm" if visible else "investigate")
            if not visible:
                bb["search_time"] = search_duration
        elif self.state in (State.CHASE, State.ATTACK):
            if not visible:
                self.fire("lost")
                bb["search_time"] = search_duration
            elif self.state == State.CHASE and bb.get("in_attack_range"):
                self.fire("in_range")
            elif self.state == State.ATTACK and not bb.get("in_attack_range"):
                self.fire("out_of_range")
        elif self.state == State.SEARCH:
            bb["search_time"] = max(0.0, bb.get("search_time", 0.0) - dt)
            if visible:
                self.fire("see_player")
            elif bb["search_time"] <= 0:
                self.fire("timeout")
        elif self.state == State.RETURN and bb.get("arrived"):
            self.fire("arrived")
        bb["action"] = self.state.name.lower()
        return bb["action"]
