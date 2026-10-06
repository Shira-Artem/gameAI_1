"""Сенсоры: конус зрения и радиус слуха."""

import math


def in_vision_cone(guard_pos, guard_dir, target_pos, fov_deg=90.0, max_dist=200.0) -> bool:
    dx, dy = target_pos[0] - guard_pos[0], target_pos[1] - guard_pos[1]
    dist = math.hypot(dx, dy)
    direction_length = math.hypot(*guard_dir)
    if dist == 0:
        return True
    if dist > max_dist or direction_length == 0:
        return False
    cos_angle = (dx * guard_dir[0] + dy * guard_dir[1]) / (dist * direction_length)
    return cos_angle >= math.cos(math.radians(fov_deg / 2))


def in_hearing_range(guard_pos, noise_pos, radius=120.0) -> bool:
    return math.dist(guard_pos, noise_pos) <= radius
