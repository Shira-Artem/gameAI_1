"""Сенсоры: конус зрения и радиус слуха."""

import math


def has_line_of_sight(start, end, obstacles=()) -> bool:
    """Стена (x, y, ширина, высота) закрывает зрение, если пересекает отрезок.

    Для каждой оси находим часть отрезка внутри границ стены.
    Если части по X и Y пересекаются, линия упирается в стену.
    """
    for x, y, width, height in obstacles:
        first, last = 0.0, 1.0
        for origin, delta, low, high in (
            (start[0], end[0] - start[0], x, x + width),
            (start[1], end[1] - start[1], y, y + height),
        ):
            if delta == 0:
                if not low <= origin <= high:
                    break
            else:
                enter, leave = sorted(((low - origin) / delta, (high - origin) / delta))
                first, last = max(first, enter), min(last, leave)
                if first > last:
                    break
        else:
            return False
    return True


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
