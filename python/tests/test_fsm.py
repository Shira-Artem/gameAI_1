from guard.bt import Status, build_guard_tree
from guard.fsm import GuardFSM, State


def test_full_cycle():
    g = GuardFSM()
    for t in ["see_player", "confirm", "in_range", "out_of_range", "lost", "timeout", "arrived"]:
        assert g.fire(t)
    assert g.state == State.PATROL


def test_bt_priority():
    bb = {"see_player": True, "hear_noise": True}
    assert build_guard_tree().tick(bb) == Status.RUNNING
    assert bb["action"] == "chase"


def test_bt_attack_has_priority_over_chase():
    bb = {"see_player": True, "in_attack_range": True}
    assert build_guard_tree().tick(bb) == Status.RUNNING
    assert bb["action"] == "attack"


def test_search_transition():
    guard = GuardFSM()
    for trigger in ("see_player", "confirm", "lost", "timeout", "arrived"):
        assert guard.fire(trigger)
    assert guard.state == State.PATROL
