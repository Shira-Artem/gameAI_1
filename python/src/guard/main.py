"""Небольшая pygame-демонстрация одной логики через FSM и Behavior Tree."""

import math
import sys

import pygame

from guard.bt import build_guard_tree
from guard.fsm import GuardFSM, State
from guard.perception import in_hearing_range, in_vision_cone

WIDTH, HEIGHT = 900, 650
WAYPOINTS = [(120, 120), (760, 120), (760, 520), (120, 520)]
VISION_DISTANCE, HEARING_RADIUS, ATTACK_DISTANCE = 220, 140, 38


def move_towards(position, target, speed, dt):
    dx, dy = target[0] - position[0], target[1] - position[1]
    distance = math.hypot(dx, dy)
    if distance == 0:
        return position, (0.0, -1.0), True
    step = min(speed * dt, distance)
    direction = (dx / distance, dy / distance)
    return (position[0] + direction[0] * step, position[1] + direction[1] * step), direction, step == distance


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    player = (450.0, 330.0)
    guard = (450.0, 120.0)
    guard_dir = (0.0, 1.0)
    waypoint_index = 0
    last_known = None
    search_time = 0.0
    alert_time = 0.0
    mode = "FSM"
    fsm, tree, bb = GuardFSM(), build_guard_tree(), {}

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                mode = "BT" if mode == "FSM" else "FSM"

        keys = pygame.key.get_pressed()
        player_direction = (float(keys[pygame.K_d]) - float(keys[pygame.K_a]),
                            float(keys[pygame.K_s]) - float(keys[pygame.K_w]))
        moving = player_direction != (0.0, 0.0)
        if moving:
            length = math.hypot(*player_direction)
            player = (max(20, min(WIDTH - 20, player[0] + player_direction[0] / length * 190 * dt)),
                      max(20, min(HEIGHT - 20, player[1] + player_direction[1] / length * 190 * dt)))

        visible = in_vision_cone(guard, guard_dir, player, max_dist=VISION_DISTANCE)
        heard = moving and in_hearing_range(guard, player, HEARING_RADIUS)
        distance = math.dist(guard, player)
        if visible or heard:
            last_known = player
        alert_time = max(0.0, alert_time - dt)

        if mode == "FSM":
            if fsm.state == State.PATROL:
                if visible or heard:
                    fsm.fire("see_player" if visible else "hear_noise")
                    alert_time = 0.35
                else:
                    guard, guard_dir, arrived = move_towards(guard, WAYPOINTS[waypoint_index], 100, dt)
                    if arrived:
                        waypoint_index = (waypoint_index + 1) % len(WAYPOINTS)
            elif fsm.state == State.ALERT:
                if alert_time <= 0:
                    if visible:
                        fsm.fire("confirm")
                    else:
                        fsm.fire("timeout")
            elif fsm.state in (State.CHASE, State.ATTACK):
                if not visible:
                    fsm.fire("lost")
                    search_time = 3.0
                elif distance <= ATTACK_DISTANCE and fsm.state == State.CHASE:
                    fsm.fire("in_range")
                elif distance > ATTACK_DISTANCE and fsm.state == State.ATTACK:
                    fsm.fire("out_of_range")
                if fsm.state == State.CHASE:
                    guard, guard_dir, _ = move_towards(guard, player, 145, dt)
            elif fsm.state == State.SEARCH:
                guard, guard_dir, arrived = move_towards(guard, last_known or guard, 90, dt)
                search_time -= dt
                if visible:
                    fsm.fire("see_player")
                elif search_time <= 0 and arrived:
                    fsm.fire("timeout")
            elif fsm.state == State.RETURN:
                guard, guard_dir, arrived = move_towards(guard, WAYPOINTS[waypoint_index], 100, dt)
                if arrived:
                    fsm.fire("arrived")
        else:
            if visible and not bb.get("see_player"):
                alert_time = 0.35
            elif bb.get("see_player") and not visible:
                search_time = 3.0
            bb.update(see_player=visible, hear_noise=heard, in_attack_range=distance <= ATTACK_DISTANCE,
                      alert_phase=alert_time > 0, searching=search_time > 0)
            tree.tick(bb)
            action = bb["action"]
            if action == "patrol":
                guard, guard_dir, arrived = move_towards(guard, WAYPOINTS[waypoint_index], 100, dt)
                if arrived:
                    waypoint_index = (waypoint_index + 1) % len(WAYPOINTS)
            elif action == "alert":
                alert_time = max(alert_time, 0.35)
            elif action == "chase":
                guard, guard_dir, _ = move_towards(guard, player, 145, dt)
            elif action == "search":
                guard, guard_dir, arrived = move_towards(guard, last_known or guard, 90, dt)
                search_time -= dt
                if arrived and search_time <= 0:
                    last_known = None

        screen.fill((24, 28, 40))
        for point in WAYPOINTS:
            pygame.draw.circle(screen, (230, 190, 70), point, 8)
            pygame.draw.circle(screen, (100, 90, 50), point, 14, 1)
        cone_angle = math.atan2(guard_dir[1], guard_dir[0])
        left = (guard[0] + math.cos(cone_angle - math.pi / 4) * VISION_DISTANCE,
                guard[1] + math.sin(cone_angle - math.pi / 4) * VISION_DISTANCE)
        right = (guard[0] + math.cos(cone_angle + math.pi / 4) * VISION_DISTANCE,
                 guard[1] + math.sin(cone_angle + math.pi / 4) * VISION_DISTANCE)
        pygame.draw.polygon(screen, (55, 105, 145), [guard, left, right], 1)
        pygame.draw.circle(screen, (80, 120, 180), (int(guard[0]), int(guard[1])), HEARING_RADIUS, 1)
        if last_known is not None and ((mode == "FSM" and fsm.state == State.SEARCH) or (mode == "BT" and search_time > 0)):
            pygame.draw.circle(screen, (245, 150, 50), (int(last_known[0]), int(last_known[1])), 14, 2)
        pygame.draw.circle(screen, (70, 210, 120), (int(player[0]), int(player[1])), 13)
        pygame.draw.circle(screen, (220, 75, 75), (int(guard[0]), int(guard[1])), 17)
        state = fsm.state.name.lower() if mode == "FSM" else bb.get("action", "patrol")
        font = pygame.font.Font(None, 26)
        lines = [f"Mode: {mode}    State/action: {state.upper()}", "WASD — move player    M — switch FSM / BT",
                 f"Vision: {'DETECTED' if visible else 'clear'}    Hearing: {'TRIGGERED' if heard else 'quiet'}"]
        for index, line in enumerate(lines):
            screen.blit(font.render(line, True, (235, 235, 235)), (18, 16 + index * 27))
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
