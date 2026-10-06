"""Небольшая pygame-демонстрация одной логики через FSM и Behavior Tree."""

import math
import sys

import pygame

from guard.bt import build_guard_tree, update_guard_tree
from guard.fsm import GuardFSM, State
from guard.perception import has_line_of_sight, in_hearing_range, in_vision_cone

WIDTH, HEIGHT = 900, 650
WAYPOINTS = [(120, 120), (760, 120), (760, 520), (120, 520)]
VISION_DISTANCE, HEARING_RADIUS, ATTACK_DISTANCE = 220, 140, 38
ALERT_TIME, SEARCH_TIME = 1.0, 10.0  # секунды; SEARCH_TIME можно сократить для проверки
TURN_SPEED = 120.0  # градусов в секунду, независимо от направления движения
OBSTACLES = [(300, 230, 30, 170), (590, 350, 30, 100)]
PLAYER_RADIUS, GUARD_RADIUS = 13, 17
HUD_HEIGHT, LEGEND_HEIGHT = 90, 96
STATE_LABELS = {
    "patrol": "ПАТРУЛЬ", "alert": "ТРЕВОГА", "chase": "ПРЕСЛЕДОВАНИЕ",
    "attack": "АТАКА", "search": "ПОИСК", "return": "ВОЗВРАТ",
}
STATE_COLORS = {
    "patrol": (220, 90, 100), "alert": (245, 165, 70), "chase": (245, 75, 85),
    "attack": (255, 55, 65), "search": (235, 185, 65), "return": (185, 115, 125),
}
MODE_LABELS = {"FSM": "FSM — Конечный автомат", "BT": "BT — Дерево поведения"}
PLAYER_COLOR = (70, 210, 120)
WAYPOINT_COLOR = (230, 190, 70)
VISION_COLOR = (95, 165, 230)
MEMORY_COLOR = (245, 150, 50)


def draw_label(surface, font, text, position, color=(235, 240, 250)):
    """Подпись с подложкой; удерживаем её внутри поверхности."""
    image = font.render(text, True, color)
    rect = image.get_rect(topleft=position).inflate(10, 4)
    rect.clamp_ip(surface.get_rect())
    pygame.draw.rect(surface, (24, 28, 40), rect, border_radius=4)
    surface.blit(image, (rect.x + 5, rect.y + 2))


def draw_waypoints(surface, font, waypoint_index):
    pygame.draw.lines(surface, (85, 78, 53), True, WAYPOINTS, 1)
    for index, point in enumerate(WAYPOINTS):
        pygame.draw.circle(surface, WAYPOINT_COLOR, point, 8)
        pygame.draw.circle(surface, WAYPOINT_COLOR, point, 15, 2 if index == waypoint_index else 1)
        draw_label(surface, font, f"Точка {index + 1}", (point[0] - 32, point[1] + 21), WAYPOINT_COLOR)
        # Маленькая стрелка на каждом отрезке показывает порядок обхода.
        target = WAYPOINTS[(index + 1) % len(WAYPOINTS)]
        direction = pygame.Vector2(target) - point
        direction = direction.normalize()
        middle = (pygame.Vector2(point) + target) / 2
        side = pygame.Vector2(-direction.y, direction.x)
        pygame.draw.lines(surface, WAYPOINT_COLOR, False,
                          [middle - direction * 8 + side * 4, middle, middle - direction * 8 - side * 4], 1)


def draw_vision(surface, guard, guard_dir, visible):
    angle = math.atan2(guard_dir[1], guard_dir[0])
    arc = [(guard[0] + math.cos(angle - math.pi / 4 + i * math.pi / 48) * VISION_DISTANCE,
            guard[1] + math.sin(angle - math.pi / 4 + i * math.pi / 48) * VISION_DISTANCE)
           for i in range(25)]
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    pygame.draw.polygon(overlay, (*VISION_COLOR, 38 if visible else 20), [guard, *arc])
    surface.blit(overlay, (0, 0))
    pygame.draw.lines(surface, VISION_COLOR, True, [guard, *arc], 2 if visible else 1)


def draw_scene(surface, fonts, player, guard, guard_dir, state, visible, heard, waypoint_index, last_known):
    surface.fill((24, 28, 40))
    small = fonts["small"]
    draw_waypoints(surface, small, waypoint_index)
    draw_vision(surface, guard, guard_dir, visible)
    center = (round(guard[0]), round(guard[1]))
    hearing_color = (130, 205, 255) if heard else (65, 110, 165)
    pygame.draw.circle(surface, hearing_color, center, HEARING_RADIUS, 3 if heard else 1)
    draw_label(surface, small, "Радиус слуха" + (" — ШУМ!" if heard else ""),
               (guard[0] - 60, guard[1] + HEARING_RADIUS + 8), hearing_color)
    if state == "search" and last_known is not None:
        pygame.draw.line(surface, MEMORY_COLOR, guard, last_known, 1)
        x, y = last_known
        pygame.draw.circle(surface, MEMORY_COLOR, (round(x), round(y)), 18, 2)
        pygame.draw.line(surface, MEMORY_COLOR, (x - 8, y - 8), (x + 8, y + 8), 3)
        pygame.draw.line(surface, MEMORY_COLOR, (x - 8, y + 8), (x + 8, y - 8), 3)
        draw_label(surface, small, "Последняя позиция игрока", (x + 22, y + 20), MEMORY_COLOR)
    # Стены поверх сектора: игрок видит, за чем можно спрятаться.
    for index, wall in enumerate(OBSTACLES):
        pygame.draw.rect(surface, (70, 77, 90), wall, border_radius=3)
        pygame.draw.rect(surface, (140, 150, 165), wall, 2, border_radius=3)
        draw_label(surface, small, f"Стена {index + 1}", (wall[0] - 18, wall[1] - 28))
    pygame.draw.circle(surface, PLAYER_COLOR, (round(player[0]), round(player[1])), 13)
    pygame.draw.circle(surface, STATE_COLORS[state], center, 17)
    direction = pygame.Vector2(guard_dir)
    tip = pygame.Vector2(guard) + direction * 45
    side = pygame.Vector2(-direction.y, direction.x)
    pygame.draw.line(surface, (245, 245, 255), guard, tip, 2)
    pygame.draw.lines(surface, (245, 245, 255), False,
                      [tip - direction * 9 + side * 5, tip, tip - direction * 9 - side * 5], 2)
    draw_label(surface, small, "ИГРОК", (player[0] - 28, player[1] - 38), PLAYER_COLOR)
    draw_label(surface, small, "ОХРАННИК", (guard[0] - 44, guard[1] + 24))
    draw_label(surface, small, STATE_LABELS[state], (guard[0] - 44, guard[1] + 46), STATE_COLORS[state])


def draw_hud(screen, fonts, mode, state, visible, heard, switch_time):
    pygame.draw.rect(screen, (32, 39, 55), (0, 0, WIDTH, HUD_HEIGHT))
    draw_label(screen, fonts["normal"], f"Режим ИИ: {MODE_LABELS[mode]}", (16, 10))
    draw_label(screen, fonts["normal"], f"Состояние: {STATE_LABELS[state]}", (16, 43), STATE_COLORS[state])
    draw_label(screen, fonts["small"], "Зрение: " + ("ИГРОК ОБНАРУЖЕН" if visible else "чисто"),
               (440, 10), VISION_COLOR)
    draw_label(screen, fonts["small"], "Слух: " + ("СЛЫШЕН ШУМ" if heard else "тихо"),
               (440, 43), (130, 205, 255) if heard else VISION_COLOR)
    draw_label(screen, fonts["small"], "WASD — движение", (725, 10))
    draw_label(screen, fonts["small"], "M — FSM / BT", (725, 43))
    top = HUD_HEIGHT + HEIGHT
    pygame.draw.rect(screen, (32, 39, 55), (0, top, WIDTH, LEGEND_HEIGHT))
    legend = [(PLAYER_COLOR, "Игрок"), ((220, 90, 100), "Охранник (цвет зависит от состояния)"),
              (WAYPOINT_COLOR, "Точки патруля и маршрут"), (VISION_COLOR, "Сектор — поле зрения"),
              (VISION_COLOR, "Круг — радиус слуха"), (MEMORY_COLOR, "Последняя известная позиция")]
    for index, (color, text) in enumerate(legend):
        x, y = 22 + (index % 2) * 440, top + 17 + (index // 2) * 27
        pygame.draw.circle(screen, color, (x, y + 7), 5)
        screen.blit(fonts["small"].render(text, True, (225, 230, 240)), (x + 14, y - 3))
    if switch_time > 0:
        text = "Управление: " + ("FSM" if mode == "FSM" else "BEHAVIOR TREE")
        image = fonts["large"].render(text, True, (245, 245, 255))
        rect = image.get_rect(center=(WIDTH // 2, HUD_HEIGHT + 45))
        pygame.draw.rect(screen, (40, 52, 75), rect.inflate(32, 20), border_radius=8)
        screen.blit(image, rect)


def move_towards(position, target, speed, dt):
    dx, dy = target[0] - position[0], target[1] - position[1]
    distance = math.hypot(dx, dy)
    if distance == 0:
        return position, (0.0, -1.0), True
    step = min(speed * dt, distance)
    direction = (dx / distance, dy / distance)
    return (position[0] + direction[0] * step, position[1] + direction[1] * step), direction, step == distance


def can_stand(position, radius, obstacles=OBSTACLES):
    """Круг не должен пересекать прямоугольную стену."""
    for x, y, width, height in obstacles:
        closest = (max(x, min(x + width, position[0])), max(y, min(y + height, position[1])))
        if math.dist(position, closest) < radius:
            return False
    return True


def move_with_collisions(position, target, radius, obstacles=OBSTACLES):
    """Мелкие шаги не дают проскочить стену; отдельно X/Y позволяют скользить вдоль неё."""
    steps = max(1, math.ceil(math.dist(position, target) / 4))
    dx, dy = (target[0] - position[0]) / steps, (target[1] - position[1]) / steps
    x, y = position
    for _ in range(steps):
        next_x = max(radius, min(WIDTH - radius, x + dx))
        if can_stand((next_x, y), radius, obstacles):
            x = next_x
        next_y = max(radius, min(HEIGHT - radius, y + dy))
        if can_stand((x, next_y), radius, obstacles):
            y = next_y
    return x, y


def turn_towards(direction, desired, dt):
    angle = math.atan2(direction[1], direction[0])
    difference = (math.atan2(desired[1], desired[0]) - angle + math.pi) % (2 * math.pi) - math.pi
    limit = math.radians(TURN_SPEED) * dt
    angle += max(-limit, min(limit, difference))
    return math.cos(angle), math.sin(angle)


def return_waypoint(position):
    """Возвращаемся к ближайшей доступной точке, чтобы не упереться в стену.

    Маршрут патруля проходит снаружи стен. Полный поиск пути здесь не нужен.
    """
    clearance = [(x - GUARD_RADIUS, y - GUARD_RADIUS, w + 2 * GUARD_RADIUS, h + 2 * GUARD_RADIUS)
                 for x, y, w, h in OBSTACLES]
    reachable = [i for i, point in enumerate(WAYPOINTS) if has_line_of_sight(position, point, clearance)]
    return min(reachable or range(len(WAYPOINTS)), key=lambda i: math.dist(position, WAYPOINTS[i]))


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT + HUD_HEIGHT + LEGEND_HEIGHT))
    pygame.display.set_caption("Игровой ИИ — охранник: конечный автомат и дерево поведения")
    scene = pygame.Surface((WIDTH, HEIGHT))
    # Системный шрифт с кириллицей, без дополнительных файлов и зависимостей.
    fonts = {name: pygame.font.SysFont("dejavusans,arial", size)
             for name, size in (("small", 16), ("normal", 20), ("large", 28))}
    switch_time = 0.0
    clock = pygame.time.Clock()
    player = (450.0, 330.0)
    guard = (450.0, 120.0)
    guard_dir = (0.0, 1.0)
    waypoint_index = 0
    last_known = None
    mode = "FSM"
    fsm, tree = GuardFSM(), build_guard_tree()
    bb = {"action": "patrol", "alert_time": 0.0, "search_time": 0.0, "arrived": False}

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        switch_time = max(0.0, switch_time - dt)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                mode = "BT" if mode == "FSM" else "FSM"
                switch_time = 1.5
                # Переключаем алгоритм, сохраняя текущую ситуацию и таймеры.
                fsm.state = State[bb["action"].upper()]

        keys = pygame.key.get_pressed()
        player_direction = (float(keys[pygame.K_d]) - float(keys[pygame.K_a]),
                            float(keys[pygame.K_s]) - float(keys[pygame.K_w]))
        old_player = player
        if player_direction != (0.0, 0.0):
            length = math.hypot(*player_direction)
            target = (player[0] + player_direction[0] / length * 190 * dt,
                      player[1] + player_direction[1] / length * 190 * dt)
            player = move_with_collisions(player, target, PLAYER_RADIUS)
        moving = math.dist(old_player, player) > 0.01

        visible = (in_vision_cone(guard, guard_dir, player, max_dist=VISION_DISTANCE)
                   and has_line_of_sight(guard, player, OBSTACLES))
        heard = moving and in_hearing_range(guard, player, HEARING_RADIUS)
        distance = math.dist(guard, player)
        if visible or heard:
            last_known = player
        bb.update(see_player=visible, hear_noise=heard, in_attack_range=distance <= ATTACK_DISTANCE)
        previous = bb["action"]
        state = (fsm.update(bb, dt, ALERT_TIME, SEARCH_TIME) if mode == "FSM"
                 else update_guard_tree(tree, bb, dt, ALERT_TIME, SEARCH_TIME))
        if state in ("return", "patrol") and previous == "search":
            waypoint_index = return_waypoint(guard)
        if state == "patrol" and previous == "return":
            waypoint_index = return_waypoint(guard)
        target, speed = guard, 0
        if state in ("patrol", "return"):
            target, speed = WAYPOINTS[waypoint_index], 100
        elif state == "chase":
            target, speed = player, 145
        elif state == "search":
            target, speed = last_known or guard, 90
        candidate, desired, _ = move_towards(guard, target, speed, dt)
        old_guard = guard
        guard = move_with_collisions(guard, candidate, GUARD_RADIUS)
        bb["arrived"] = math.dist(guard, target) < 4
        if state == "patrol" and bb["arrived"]:
            waypoint_index = (waypoint_index + 1) % len(WAYPOINTS)
        if state in ("alert", "attack") and last_known is not None:
            desired = (last_known[0] - guard[0], last_known[1] - guard[1])
        elif state == "search" and math.dist(guard, old_guard) < 0.1:
            # У последней позиции (или стены) охранник осматривается, а не стоит неподвижно.
            angle = math.atan2(guard_dir[1], guard_dir[0]) + math.radians(45) * dt
            desired = (math.cos(angle), math.sin(angle))
        if desired != (0.0, 0.0):
            guard_dir = turn_towards(guard_dir, desired, dt)
        if state == "patrol" and previous in ("search", "return"):
            last_known = None

        draw_scene(scene, fonts, player, guard, guard_dir, state, visible, heard, waypoint_index, last_known)
        screen.blit(scene, (0, HUD_HEIGHT))
        draw_hud(screen, fonts, mode, state, visible, heard, switch_time)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
