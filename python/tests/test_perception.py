import pytest

from guard.perception import has_line_of_sight, in_hearing_range, in_vision_cone


def test_vision_cone_and_distance():
    assert in_vision_cone((0, 0), (1, 0), (100, 0), fov_deg=90, max_dist=120)
    assert not in_vision_cone((0, 0), (1, 0), (100, 100), fov_deg=90, max_dist=200)
    assert not in_vision_cone((0, 0), (1, 0), (130, 0), max_dist=120)


def test_vision_zero_direction_is_safe():
    assert not in_vision_cone((0, 0), (0, 0), (10, 0))
    assert in_vision_cone((0, 0), (0, 0), (0, 0))


def test_hearing_radius():
    assert in_hearing_range((0, 0), (3, 4), radius=5)
    assert not in_hearing_range((0, 0), (6, 0), radius=5)


@pytest.mark.parametrize("start,end,clear", [
    ((0, 0), (100, 0), False),
    ((100, 0), (0, 0), False),
    ((0, 30), (100, 30), True),
    ((0, -50), (100, 50), False),
    ((50, -50), (50, 50), False),
    ((0, 0), (30, 0), True),
    ((45, 0), (100, 0), False),
])
def test_wall_blocks_only_intersecting_line(start, end, clear):
    assert has_line_of_sight(start, end, [(40, -10, 20, 20)]) == clear
