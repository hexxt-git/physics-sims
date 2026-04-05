from __future__ import annotations

from typing import Any, cast

import numpy as np
from pyray import *  # pyright: ignore[reportWildcardImportFromLibrary]
from pyray import ffi
from raylib import rl

# Target window size (px). Simulation resolution follows from SCALE.
# SCALE = screen pixels per simulation cell (float OK; <1 means finer grid, larger COLS×ROWS).
TARGET_WIDTH = 1000
TARGET_HEIGHT = 700
SCALE = 2

COLS = max(1, int(round(TARGET_WIDTH / SCALE)))
ROWS = max(1, int(round(TARGET_HEIGHT / SCALE)))
WIDTH = int(round(COLS * SCALE))
HEIGHT = int(round(ROWS * SCALE))

# Double-slit experiment (fractions of COLS / ROWS; col 0 = left, row 0 = top).
BARRIER_X_FRAC = 1.0 / 3.0  # wall center at one-third across the screen
BARRIER_THICK_FRAC = 0.015  # column span of the wall
SLIT_HEIGHT_FRAC = 0.04  # vertical opening of each slit
SLIT_SEP_FRAC = 0.14  # center-to-center distance between the two slits
SOURCE_X_FRAC = -0.3  # light source circle center (left of barrier)
SOURCE_RADIUS_FRAC = 0.8  # circle radius vs min(COLS, ROWS)
# Driven point on the circle perimeter (angle 0 = rightmost point); height oscillates each frame.
VIB_AMPLITUDE = 1.0
VIB_OMEGA = 2.0 * np.pi / 45.0  # radians per frame (~45 frames per cycle)

# --- Optics masks (shape ROWS × COLS; row = y, col = x) -----------------
# mirror_mask: True where the surface is rigid — height is fixed, speed forced to 0.
# mirror_height: fixed height field on mirror cells (e.g. 0 for flat, curved for a mirror shape).
# lens_mass: >= 1.0 everywhere; > 1 means “heavier” — same pressure, less acceleration.
#            Ignored on mirror cells (mirrors override).


def double_slit_barrier_mask() -> np.ndarray:
    """Vertical mirror band with two horizontal gaps (holes) through it."""
    fw = float(COLS)
    fh = float(ROWS)
    mid_row = 0.5 * (ROWS - 1)
    thick = max(2.0, BARRIER_THICK_FRAC * fw)
    c_mid = BARRIER_X_FRAC * fw
    c0 = int(round(c_mid - 0.5 * thick))
    c1 = int(round(c_mid + 0.5 * thick))
    c0 = max(0, min(COLS - 1, c0))
    c1 = max(0, min(COLS - 1, c1))
    if c0 > c1:
        c0, c1 = c1, c0

    sl_h = max(2.0, SLIT_HEIGHT_FRAC * fh)
    sl_sep = max(sl_h + 2.0, SLIT_SEP_FRAC * fh)
    s1 = mid_row - 0.5 * sl_sep
    s2 = mid_row + 0.5 * sl_sep

    ii, jj = np.indices((ROWS, COLS), dtype=np.float64)
    in_wall = (jj >= c0) & (jj <= c1)
    in_s1 = (ii >= s1 - 0.5 * sl_h) & (ii <= s1 + 0.5 * sl_h)
    in_s2 = (ii >= s2 - 0.5 * sl_h) & (ii <= s2 + 0.5 * sl_h)
    return in_wall & ~(in_s1 | in_s2)


def build_optics() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Double-slit: rigid wall with two openings; uniform lens mass."""
    mirror_mask = np.zeros((ROWS, COLS), dtype=bool)
    mirror_height = np.zeros((ROWS, COLS), dtype=np.float64)
    lens_mass = np.ones((ROWS, COLS), dtype=np.float64)

    mirror_mask |= double_slit_barrier_mask()

    return mirror_mask, mirror_height, lens_mass


mirror_mask, mirror_height, lens_mass = build_optics()

# Flat field; a single pixel on the source circle’s outer wall is driven each frame.
cx = SOURCE_X_FRAC * (COLS - 1)
cy = 0.5 * (ROWS - 1)
radius = SOURCE_RADIUS_FRAC * float(min(COLS, ROWS))
# One pixel on the perimeter (θ = 0 → rightmost point); clamp to grid.
_theta0 = 0.0
source_col = int(np.clip(round(cx + radius * np.cos(_theta0)), 0, COLS - 1))
source_row = int(np.clip(round(cy + radius * np.sin(_theta0)), 0, ROWS - 1))
# Avoid driving a mirror cell (e.g. if geometry overlaps the wall).
for _dtheta in np.linspace(0.0, 2.0 * np.pi, num=32, endpoint=False):
    sc = int(np.clip(round(cx + radius * np.cos(_dtheta)), 0, COLS - 1))
    sr = int(np.clip(round(cy + radius * np.sin(_dtheta)), 0, ROWS - 1))
    if not mirror_mask[sr, sc]:
        source_col, source_row = sc, sr
        break

height = np.zeros((ROWS, COLS), dtype=np.float64)
height = np.where(mirror_mask, mirror_height, height)
speed = np.zeros_like(height)
vib_phase = 0.0

_ones = np.ones((ROWS, COLS), dtype=np.float64)
has_up = _ones.copy()
has_up[0, :] = 0.0
has_down = _ones.copy()
has_down[-1, :] = 0.0
has_left = _ones.copy()
has_left[:, 0] = 0.0
has_right = _ones.copy()
has_right[:, -1] = 0.0
neighbor_count = has_up + has_down + has_left + has_right


def neighbor_average(h: np.ndarray) -> np.ndarray:
    up = np.zeros_like(h)
    up[1:, :] = h[:-1, :]
    down = np.zeros_like(h)
    down[:-1, :] = h[1:, :]
    left = np.zeros_like(h)
    left[:, 1:] = h[:, :-1]
    right = np.zeros_like(h)
    right[:, :-1] = h[:, 1:]
    s = up + down + left + right
    return np.where(neighbor_count > 0, s / neighbor_count, h)


def step(
    height_grid: np.ndarray,
    speed_grid: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    # Lock mirror surface before forces so neighbors see the correct boundary.
    locked_height = np.where(mirror_mask, mirror_height, height_grid)
    locked_speed = np.where(mirror_mask, 0.0, speed_grid)
    # Perturbation eta = h - h_optics. Using delta = h - avg(h) injects a bogus drive
    # whenever mirror_height is curved: (h0 - avg(h0)) ≠ 0, so fluid near the mirror
    # is constantly pushed. Evolving eta removes that static mismatch.
    surface_perturbation = locked_height - mirror_height
    average_perturbation = neighbor_average(surface_perturbation)
    difference_from_neighbors = surface_perturbation - average_perturbation
    acceleration = difference_from_neighbors / lens_mass
    next_speed = locked_speed - acceleration
    next_height = locked_height + next_speed
    next_height = np.where(mirror_mask, mirror_height, next_height)
    next_speed = np.where(mirror_mask, 0.0, next_speed)
    return next_height, next_speed


def heights_to_rgba(h: np.ndarray, out: np.ndarray) -> None:
    v = np.clip(np.power(np.abs(h), 0.8) * 255.0, 0.0, 255.0).astype(np.uint8)
    out[..., 0] = v
    out[..., 1] = v
    out[..., 2] = v
    out[..., 3] = 255
    out[..., 0] = np.where(mirror_mask, (out[..., 0].astype(np.int16) + 35).clip(0, 255), out[..., 0])
    out[..., 2] = np.where(
        (~mirror_mask) & (lens_mass > 1.01),
        (out[..., 2].astype(np.int16) + 25).clip(0, 255),
        out[..., 2],
    )


init_window(WIDTH, HEIGHT, "Double-slit")

pixel_buf = np.zeros((ROWS, COLS, 4), dtype=np.uint8)
img = gen_image_color(COLS, ROWS, RAYWHITE)
tex = load_texture_from_image(img)
unload_image(img)


def upload_texture() -> None:
    heights_to_rgba(height, pixel_buf)
    ptr = ffi.cast("void *", ffi.from_buffer(pixel_buf))
    cast(Any, rl).UpdateTexture(tex, ptr)


while not window_should_close():
    begin_drawing()
    clear_background(RAYWHITE)
    upload_texture()
    draw_texture_ex(tex, Vector2(0, 0), 0.0, float(SCALE), WHITE)
    end_drawing()

    height, speed = step(height, speed)
    vib_phase += VIB_OMEGA
    height[source_row, source_col] = VIB_AMPLITUDE * float(np.sin(vib_phase))

unload_texture(tex)
close_window()
