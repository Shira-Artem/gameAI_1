import math

import pytest

from guard.bt import build_guard_tree, update_guard_tree
from guard.fsm import GuardFSM
from guard.main import (
    ALERT_TIME,
    GUARD_RADIUS,
    OBSTACLES,
    PLAYER_RADIUS,
    SEARCH_TIME,
    TURN_SPEED,
    WAYPOINTS,
    can_stand,
    move_with_collisions,
    return_waypoint,
    turn_towards,
)
from guard.perception import has_line_of_sight, in_vision_cone


@pytest.fixture(params=["FSM", "BT"])
def controller(request):
    bb = {"action": "patrol", "see_player": False, "hear_noise": False, "in_attack_range": False}
    if request.param == "FSM":
        fsm = GuardFSM()

        def tick(dt):
            return fsm.update(bb, dt, ALERT_TIME, SEARCH_TIME)
    else:
        tree = build_guard_tree()

        def tick(dt):
            return update_guard_tree(tree, bb, dt, ALERT_TIME, SEARCH_TIME)
    return request.param, bb, tick


def test_alert_counts_down_even_with_continuous_detection(controller):
    _, bb, tick = controller
    bb.update(see_player=True, hear_noise=True)
    assert tick(0.1) == "alert"
    for _ in range(9):
        assert tick(0.1) == "alert"
    assert bb["alert_time"] == pytest.approx(0.1)
    assert tick(0.11) == "chase"
    # Повторная видимость не запускает новую тревогу каждый кадр.
    assert tick(0.1) == "chase"
    bb["in_attack_range"] = True
    assert tick(0.1) == "attack"
    bb["in_attack_range"] = False
    assert tick(0.1) == "chase"


def test_hearing_only_leads_to_search_not_endless_alert(controller):
    _, bb, tick = controller
    bb["hear_noise"] = True
    assert tick(0.1) == "alert"
    assert tick(1.01) == "search"
    assert bb["search_time"] == SEARCH_TIME
    # Даже продолжающийся шум не имеет приоритета над уже начатым поиском.
    assert tick(0.1) == "search"
    assert bb["alert_time"] == 0


def test_wall_hides_player_then_search_returns_to_patrol(controller):
    mode, bb, tick = controller
    guard, player, direction = (250, 300), (380, 300), (1, 0)
    assert in_vision_cone(guard, direction, player)
    bb["see_player"] = True
    assert tick(0.1) == "alert"
    assert tick(1.01) == "chase"
    bb["see_player"] = has_line_of_sight(guard, player, OBSTACLES)
    assert not bb["see_player"]
    assert tick(0.1) == "search"
    assert tick(SEARCH_TIME - 0.1) == "search"
    state = tick(0.2)
    if mode == "FSM":
        assert state == "return"
        bb["arrived"] = False
        assert tick(0.1) == "return"
        bb["arrived"] = True
        state = tick(0.1)
    assert state == "patrol"


def test_player_can_be_found_again_during_search(controller):
    _, bb, tick = controller
    bb["hear_noise"] = True
    tick(0.1)
    assert tick(1.01) == "search"
    bb.update(see_player=True, hear_noise=False)
    assert tick(0.1) == "chase"


def test_close_detection_still_has_one_second_alert(controller):
    _, bb, tick = controller
    bb.update(see_player=True, in_attack_range=True)
    assert tick(0.1) == "alert"
    assert tick(0.5) == "alert"
    state = tick(0.51)
    # FSM проходит через CHASE, BT сразу выбирает приоритетную атаку.
    if state == "chase":
        state = tick(0.1)
    assert state == "attack"


@pytest.mark.parametrize("radius", [PLAYER_RADIUS, GUARD_RADIUS])
def test_characters_cannot_cross_wall_even_with_large_step(radius):
    result = move_with_collisions((250, 300), (380, 300), radius)
    assert result[0] <= 300 - radius
    assert can_stand(result, radius)


def test_collision_allows_sliding_along_wall():
    result = move_with_collisions((280, 260), (380, 350), GUARD_RADIUS)
    assert result[0] <= 300 - GUARD_RADIUS
    assert result[1] > 260


def test_turn_is_limited_and_handles_angle_wrap():
    dt = 0.1
    result = turn_towards((1, 0), (0, 1), dt)
    assert math.degrees(math.atan2(result[1], result[0])) == pytest.approx(TURN_SPEED * dt)
    old = (math.cos(math.radians(179)), math.sin(math.radians(179)))
    desired = (math.cos(math.radians(-179)), math.sin(math.radians(-179)))
    assert turn_towards(old, desired, dt) == pytest.approx(desired)


@pytest.mark.parametrize("position", [(350, 320), (440, 440), (560, 320)])
def test_return_uses_reachable_waypoint_and_patrol_route_is_clear(position):
    target = WAYPOINTS[return_waypoint(position)]
    assert move_with_collisions(position, target, GUARD_RADIUS) == pytest.approx(target)
    for index, start in enumerate(WAYPOINTS):
        target = WAYPOINTS[(index + 1) % len(WAYPOINTS)]
        assert move_with_collisions(start, target, GUARD_RADIUS) == pytest.approx(target)
