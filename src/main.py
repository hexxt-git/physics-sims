from pyray import *  # pyright: ignore[reportWildcardImportFromLibrary]
from raylib import KEY_LEFT_SHIFT, KEY_SPACE, MOUSE_BUTTON_LEFT, SetTargetFPS # pyright: ignore[reportWildcardImportFromLibrary]
from models import Ball, Line, Connection
import math

WIDTH = 800
HEIGHT = 600

init_window(WIDTH, HEIGHT, "Physics Simulation")
SetTargetFPS(60)

REFLECTION_COEFFICIENT = 0.9
FRICTION_COEFFICIENT = 0.99
STEPS = 10

balls: list[Ball] = []
lines: list[Line] = []
connections: list[Connection] = []

def get_ball_by_id(id: int) -> Ball:
    for ball in balls:
        if ball.id == id:
            return ball
    raise ValueError(f"Ball with id {id} not found")

def calc_mass(radius: float) -> float:
    return math.pi * radius ** 2 * 100

walls = [
    # TOP
    Line(x1=WIDTH, y1=0, x2=0, y2=0),
    # BOTTOM
    Line(x1=0, y1=HEIGHT, x2=WIDTH, y2=HEIGHT),
    # LEFT
    Line(x1=0, y1=0, x2=0, y2=HEIGHT),
    # RIGHT
    Line(x1=WIDTH, y1=HEIGHT, x2=WIDTH, y2=0),
]

lines.extend(walls)

TOWER_WIDTH = 6
TOWER_HEIGHT = 5
TOWER_START_X = 100
TOWER_START_Y = 100
TOWER_SPACING = 40

# creating a tower of balls
layers: list[list[Ball]] = []
for layer in range(TOWER_HEIGHT):
    layerBalls: list[Ball] = []
    for collumn in range(TOWER_WIDTH):
        ball = Ball(x=TOWER_START_X+collumn*TOWER_SPACING, y=TOWER_START_Y+layer*TOWER_SPACING+collumn*10, radius=7, color=WHITE)
        if collumn > 0:
            prev_ball = layerBalls[collumn - 1]
            connections.append(Connection(ball.id, prev_ball.id, TOWER_SPACING, force=1))
        if layer > 0:
            prev_layer_ball = layers[layer-1][collumn]
            connections.append(Connection(ball.id, prev_layer_ball.id, TOWER_SPACING, force=1))
            if collumn > 0:
                prev_layer_prev_ball = layers[layer-1][collumn-1]
                connections.append(Connection(ball.id, prev_layer_prev_ball.id, TOWER_SPACING * math.sqrt(2), force=1))
            if collumn < TOWER_WIDTH - 1:
                next_layer_ball = layers[layer-1][collumn+1]
                connections.append(Connection(ball.id, next_layer_ball.id, TOWER_SPACING * math.sqrt(2), force=1))
        layerBalls.append(ball)
    layers.append(layerBalls)
    balls.extend(layerBalls)

layers = []
for layer in range(TOWER_HEIGHT):
    layerBalls = []
    for collumn in range(TOWER_WIDTH):
        ball = Ball(x=TOWER_START_X+300+collumn*TOWER_SPACING, y=TOWER_START_Y+layer*TOWER_SPACING+collumn*10, radius=7, color=WHITE)
        if collumn > 0:
            prev_ball = layerBalls[collumn - 1]
            connections.append(Connection(ball.id, prev_ball.id, TOWER_SPACING, force=0.1))
        if layer > 0:
            prev_layer_ball = layers[layer-1][collumn]
            connections.append(Connection(ball.id, prev_layer_ball.id, TOWER_SPACING, force=0.1))
            if collumn > 0:
                prev_layer_prev_ball = layers[layer-1][collumn-1]
                connections.append(Connection(ball.id, prev_layer_prev_ball.id, TOWER_SPACING * math.sqrt(2), force=0.1))
            if collumn < TOWER_WIDTH - 1:
                next_layer_ball = layers[layer-1][collumn+1]
                connections.append(Connection(ball.id, next_layer_ball.id, TOWER_SPACING * math.sqrt(2), force=0.1))
        layerBalls.append(ball)
    layers.append(layerBalls)
    balls.extend(layerBalls)



def render_and_clear():
    clear_background(BLACK)
    for ball in balls:
        draw_circle(int(ball.x), int(ball.y), ball.radius, ball.color)
    for line in lines:
        draw_line_ex(Vector2(line.x1, line.y1), Vector2(line.x2, line.y2), 1, WHITE)
    for connection in connections:
        draw_line_ex(
            Vector2(get_ball_by_id(connection.ball1_id).x, get_ball_by_id(connection.ball1_id).y),
            Vector2(get_ball_by_id(connection.ball2_id).x, get_ball_by_id(connection.ball2_id).y),
            1, WHITE
        )

def update():
    for ball in balls:
        ball.vx = max(min(ball.vx, 10), -10)
        ball.vy = max(min(ball.vy, 10), -10)

        ball.x += ball.vx / STEPS
        ball.y += ball.vy / STEPS
        ball.vy += 0.25 / STEPS

        for line in lines:
            # check that the ball's bounding box overlaps with the line's bounding box
            ball_left = ball.x - ball.radius
            ball_right = ball.x + ball.radius
            ball_top = ball.y - ball.radius
            ball_bottom = ball.y + ball.radius
            
            line_left = min(line.x1, line.x2)
            line_right = max(line.x1, line.x2)
            line_top = min(line.y1, line.y2)
            line_bottom = max(line.y1, line.y2)
            
            if (ball_right < line_left or ball_left > line_right or 
                ball_bottom < line_top or ball_top > line_bottom):
                continue

            # the direction vector of a line is (-dy, dx) or (dy, -dx) and it depends on which side the ball is on
            directionX = -(line.y2 - line.y1)
            directionY = line.x2 - line.x1

            # normalizing the direction vector
            magnitude = math.sqrt(directionX ** 2 + directionY ** 2)
            normalX = directionX / magnitude
            normalY = directionY / magnitude

            # vector from line center to ball
            X = ball.x - (line.x1 + line.x2) /2
            Y = ball.y - (line.y1 + line.y2) /2

            # signed distance from the line to the ball
            signed_distance = X * normalX + Y * normalY

            if signed_distance > 0:
                normalX = -normalX
                normalY = -normalY

            distance = abs(signed_distance)

            if distance < ball.radius:
                # handling corners
                distance_to_c1 = math.sqrt((ball.x - line.x1) ** 2 + (ball.y - line.y1) ** 2)
                distance_to_c2 = math.sqrt((ball.x - line.x2) ** 2 + (ball.y - line.y2) ** 2)
                if distance_to_c1 < ball.radius:
                    # new normal vector is facing the ball and no sliding full bounce since speed_along_tanget would be 0
                    normalX = (line.x1 - ball.x) / distance_to_c1
                    normalY = (line.y1 - ball.y) / distance_to_c1

                    # full bounce reflection for corner collision
                    speed_along_normal = ball.vx * normalX + ball.vy * normalY
                    if speed_along_normal > 0:
                        ball.vx = -speed_along_normal * normalX * REFLECTION_COEFFICIENT
                        ball.vy = -speed_along_normal * normalY * REFLECTION_COEFFICIENT

                elif distance_to_c2 < ball.radius:
                    normalX = (line.x2 - ball.x) / distance_to_c2
                    normalY = (line.y2 - ball.y) / distance_to_c2

                    speed_along_normal = ball.vx * normalX + ball.vy * normalY
                    if speed_along_normal > 0:
                        ball.vx = -speed_along_normal * normalX * REFLECTION_COEFFICIENT
                        ball.vy = -speed_along_normal * normalY * REFLECTION_COEFFICIENT

                else:
                    # handling mid line collision
                    speed_along_normal = ball.vx * normalX + ball.vy * normalY
                    speed_along_tangent = ball.vx * normalY - ball.vy * normalX
                    if speed_along_normal > 0:
                        # Reflect: reverse normal component, keep tangent component
                        ball.vx = -speed_along_normal * normalX * REFLECTION_COEFFICIENT + speed_along_tangent * normalY * FRICTION_COEFFICIENT
                        ball.vy = -speed_along_normal * normalY * REFLECTION_COEFFICIENT - speed_along_tangent * normalX * FRICTION_COEFFICIENT

                        overlap = ball.radius - distance
                        ball.x -= overlap * normalX / 2
                        ball.y -= overlap * normalY / 2

        for other_ball in balls:
            if other_ball == ball:
                continue
            distance = math.sqrt((ball.x - other_ball.x) ** 2 + (ball.y - other_ball.y) ** 2)
            
            if not (distance < ball.radius + other_ball.radius):
                continue

            normalX = (other_ball.x - ball.x) / distance
            normalY = (other_ball.y - ball.y) / distance

            mass1 = calc_mass(ball.radius)
            mass2 = calc_mass(other_ball.radius)
            massTotal = mass1 + mass2
            
            
            relative_velocity_x = ball.vx - other_ball.vx
            relative_velocity_y = ball.vy - other_ball.vy
            
            speed_along_normal = relative_velocity_x * normalX + relative_velocity_y * normalY

            if speed_along_normal > 0:
                # bounce force
                force_x = speed_along_normal * normalX * REFLECTION_COEFFICIENT
                force_y = speed_along_normal * normalY * REFLECTION_COEFFICIENT
                
                ball.vx -= force_x * mass2 / massTotal
                ball.vy -= force_y * mass2 / massTotal
                other_ball.vx += force_x * mass1 / massTotal
                other_ball.vy += force_y * mass1 / massTotal

            overlap = ball.radius + other_ball.radius - distance
            ball.x -= overlap * normalX * mass2 / massTotal
            ball.y -= overlap * normalY * mass2 / massTotal
            other_ball.x += overlap * normalX * mass1 / massTotal
            other_ball.y += overlap * normalY * mass1 / massTotal

    for connection in connections:
        ball1 = get_ball_by_id(connection.ball1_id)
        ball2 = get_ball_by_id(connection.ball2_id)

        deltaX = ball1.x + ball1.vx - ball2.x - ball2.vx
        deltaY = ball1.y + ball1.vy - ball2.y - ball2.vy

        actual_distance = math.sqrt(deltaX ** 2 + deltaY ** 2)
        error = actual_distance - connection.length

        normalX = deltaX / actual_distance
        normalY = deltaY / actual_distance

        mass1 = calc_mass(ball1.radius)
        mass2 = calc_mass(ball2.radius)
        massTotal = mass1 + mass2

        ball1.vx -= error * normalX * connection.force * mass2 / massTotal
        ball1.vy -= error * normalY * connection.force * mass2 / massTotal
        ball2.vx += error * normalX * connection.force * mass1 / massTotal
        ball2.vy += error * normalY * connection.force * mass1 / massTotal


while not window_should_close():
    begin_drawing()
    
    for _ in range(STEPS):
        update()
    render_and_clear()

    if is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
        balls.append(Ball(x=get_mouse_x(), y=get_mouse_y(), radius=10, color=WHITE))
        if is_key_down(KEY_LEFT_SHIFT):
            connections.append(Connection(ball1_id=balls[-1].id, ball2_id=balls[-2].id, length=30))
        if is_key_down(KEY_SPACE):
            balls[-1].radius = 40

    draw_fps(10, 10)

    end_drawing()

close_window()