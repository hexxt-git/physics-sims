from random import random, randint
from pyray import *  # pyright: ignore[reportWildcardImportFromLibrary]
from raylib import SetTargetFPS # pyright: ignore[reportWildcardImportFromLibrary]
from models import Ball, Line
import math

WIDTH = 800
HEIGHT = 600

init_window(WIDTH, HEIGHT, "Physics Simulation")
SetTargetFPS(60)

REFLECTION_COEFFICIENT = 0.7
FRICTION_COEFFICIENT = 0.99
STEPS = 10

balls = [
    Ball(x=100, y=100, radius=25, color=RED),
    Ball(x=200, y=200, radius=25, color=BLUE),
    Ball(x=500, y=100, radius=25, color=PURPLE),
]
for i in range(100):
    balls.append(
        Ball(
            x=random() * (WIDTH - 40) + 20,
            y=random() * 100 + 40,
            radius=randint(10, 30),
            color=GREEN,
        )
    )

lines = [
    Line(x1=150, y1=400, x2=600, y2=250),
    Line(x1=100, y1=200, x2=300, y2=500),

    # TOP
    Line(x1=WIDTH, y1=0, x2=0, y2=0),
    Line(x1=WIDTH, y1=10, x2=0, y2=10),
    # BOTTOM
    Line(x1=0, y1=HEIGHT, x2=WIDTH, y2=HEIGHT),
    Line(x1=0, y1=HEIGHT-10, x2=WIDTH, y2=HEIGHT-10),
    # LEFT
    Line(x1=0, y1=0, x2=0, y2=HEIGHT),
    Line(x1=10, y1=0, x2=10, y2=HEIGHT),
    # RIGHT
    Line(x1=WIDTH, y1=HEIGHT, x2=WIDTH, y2=0),
    Line(x1=WIDTH-10, y1=HEIGHT, x2=WIDTH-10, y2=0),
]

def render_and_clear():
    clear_background(WHITE)
    for ball in balls:
        draw_circle(int(ball.x), int(ball.y), ball.radius, ball.color)
    for line in lines:
        draw_line_ex(Vector2(line.x1, line.y1), Vector2(line.x2, line.y2), 3, BLACK)

def update():
    for ball in balls:
        ball.x += ball.vx / STEPS
        ball.y += ball.vy / STEPS
        ball.vy += 0.2 / STEPS

        for line in lines:
            # the direction vector of a line is (-dy, dx)
            directionX = -(line.y2 - line.y1)
            directionY = line.x2 - line.x1

            # normalizing the direction vector
            magnitude = math.sqrt(directionX ** 2 + directionY ** 2)
            normalX = directionX / magnitude
            normalY = directionY / magnitude

            X = ball.x - (line.x1 + line.x2) /2
            Y = ball.y - (line.y1 + line.y2) /2

            distance = abs(X * normalX + Y * normalY)

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


            if distance < ball.radius:
                # handling corners
                distance_to_c1 = math.sqrt((ball.x - line.x1) ** 2 + (ball.y - line.y1) ** 2)
                distance_to_c2 = math.sqrt((ball.x - line.x2) ** 2 + (ball.y - line.y2) ** 2)
                if distance_to_c1 < ball.radius and False:
                    pass
                    # # new normal vector is facing the ball and no sliding full bounce since speed_along_tanget would be 0
                    # normalX = (line.x1 - ball.x) / distance_to_c1
                    # normalY = (line.y1 - ball.y) / distance_to_c1

                    # # full bounce reflection for corner collision
                    # speed_along_normal = ball.vx * normalX + ball.vy * normalY
                    # if speed_along_normal > 0:
                    #     ball.vx = -speed_along_normal * normalX * REFLECTION_COEFFICIENT
                    #     ball.vy = -speed_along_normal * normalY * REFLECTION_COEFFICIENT

                elif distance_to_c2 < ball.radius and False:
                    pass
                    # normalX = (line.x2 - ball.x) / distance_to_c2
                    # normalY = (line.y2 - ball.y) / distance_to_c2

                    # speed_along_normal = ball.vx * normalX + ball.vy * normalY
                    # if speed_along_normal > 0:
                    #     ball.vx = -speed_along_normal * normalX * REFLECTION_COEFFICIENT
                    #     ball.vy = -speed_along_normal * normalY * REFLECTION_COEFFICIENT

                else:
                    # handling mid line collision
                    speed_along_normal = ball.vx * normalX + ball.vy * normalY
                    speed_along_tangent = ball.vx * normalY - ball.vy * normalX
                    if speed_along_normal > 0:
                        # Reflect: reverse normal component, keep tangent component
                        ball.vx = -speed_along_normal * normalX * REFLECTION_COEFFICIENT + speed_along_tangent * normalY * FRICTION_COEFFICIENT
                        ball.vy = -speed_along_normal * normalY * REFLECTION_COEFFICIENT - speed_along_tangent * normalX * FRICTION_COEFFICIENT

        for other_ball in balls:
            if other_ball == ball:
                continue
            distance = math.sqrt((ball.x - other_ball.x) ** 2 + (ball.y - other_ball.y) ** 2)
            
            if distance < ball.radius + other_ball.radius:
                normalX = (other_ball.x - ball.x) / distance
                normalY = (other_ball.y - ball.y) / distance
                
                relative_velocity_x = ball.vx - other_ball.vx
                relative_velocity_y = ball.vy - other_ball.vy
                
                speed_along_normal = relative_velocity_x * normalX + relative_velocity_y * normalY
                speed_along_tangent = relative_velocity_x * normalY - relative_velocity_y * normalX

                if speed_along_normal > 0:
                    # bounce force
                    force_x = speed_along_normal * normalX * REFLECTION_COEFFICIENT
                    force_y = speed_along_normal * normalY * REFLECTION_COEFFICIENT

                    # no bounce force
                    force_x += speed_along_normal / 2 * normalX * (1 - REFLECTION_COEFFICIENT)
                    force_y += speed_along_normal / 2 * normalY * (1 - REFLECTION_COEFFICIENT)

                    ball.vx -= force_x
                    ball.vy -= force_y
                    other_ball.vx += force_x
                    other_ball.vy += force_y

                overlap = ball.radius + other_ball.radius - distance
                ball.x -= overlap * normalX / 2 / 2
                ball.y -= overlap * normalY / 2 / 2
                other_ball.x += overlap * normalX / 2 / 2
                other_ball.y += overlap * normalY / 2 / 2

while not window_should_close():
    begin_drawing()
    
    for _ in range(STEPS):
        update()
    render_and_clear()

    draw_fps(10, 10)

    end_drawing()

close_window()