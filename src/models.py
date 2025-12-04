from dataclasses import dataclass, field
import random
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
    id: int = field(default_factory=lambda: random.randint(0, 1000000))

@dataclass
class Connection:
    ball1_id: int
    ball2_id: int
    length: float
    force: float = 0.01