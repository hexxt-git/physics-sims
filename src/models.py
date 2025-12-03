from dataclasses import dataclass

from pyray import Color

@dataclass
class Line:
    x1: float
    y1: float
    x2: float
    y2: float

@dataclass
class Ball:
    x: float
    y: float
    radius: float
    color: Color
    vx: float = 0
    vy: float = 0