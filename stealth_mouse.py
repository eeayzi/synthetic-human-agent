"""
stealth_mouse.py

Bézier curve mathematics, path generation,
validation, and smooth cursor movement for
ordinary desktop UI automation.
"""

import math



# ------------------------------------------
# 1. Calculate one point on a cubic Bezier curve
# ------------------------------------------

def bezier_point(p0, p1, p2, p3, t):
    """
    Calculate one point on a cubic Bezier curve.

    p0: starting point (x, y)
    p1: first control point (x, y)
    p2: second control point (x, y)
    p3: ending point (x, y)
    t: parameter between 0 and 1

    Returns:
        A tuple (x, y).
    """

    if not 0 <= t <= 1:
        raise ValueError("t must be between 0 and 1")

    x = (
        (1 - t) ** 3 * p0[0]
        + 3 * (1 - t) ** 2 * t * p1[0]
        + 3 * (1 - t) * t ** 2 * p2[0]
        + t ** 3 * p3[0]
    )

    y = (
        (1 - t) ** 3 * p0[1]
        + 3 * (1 - t) ** 2 * t * p1[1]
        + 3 * (1 - t) * t ** 2 * p2[1]
        + t ** 3 * p3[1]
    )

    return (x, y)


# ------------------------------------------
# 2. Generate a complete Bezier path
# ------------------------------------------

def generate_bezier_path(p0, p1, p2, p3, steps=50):
    """
    Generate points along a cubic Bezier curve.

    steps determines the number of intervals.
    The returned list contains steps + 1 points.
    """

    if not isinstance(steps, int) or isinstance(steps, bool):
        raise TypeError("steps must be an integer")

    if steps < 1:
        raise ValueError("steps must be at least 1")

    points = []

    for i in range(steps + 1):
        t = i / steps

        point = bezier_point(
            p0, p1, p2, p3, t
        )

        points.append(point)

    return points


# ------------------------------------------
# 3. Measure distance between two points
# ------------------------------------------

def distance_between(p1, p2):
    """
    Calculate straight-line distance between
    two points in 2D space.
    """

    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    return math.hypot(dx, dy)


# ------------------------------------------
# 4. Validate a generated path
# ------------------------------------------

def validate_path(points, expected_start, expected_end):
    """
    Check that a path is non-empty and starts
    and ends at the expected coordinates.
    """

    if not points:
        raise ValueError("Path cannot be empty")

    if not all(math.isfinite(v) for point in [*points, expected_start, expected_end] for v in point):
        raise ValueError("Path coordinates must be finite")

    tolerance = 1e-6

    if distance_between(
        points[0], expected_start
    ) > tolerance:
        raise ValueError("Incorrect starting point")

    if distance_between(
        points[-1], expected_end
    ) > tolerance:
        raise ValueError("Incorrect ending point")

    return True


# ------------------------------------------
# 5. Move the cursor in an ordinary UI
# ------------------------------------------

def move_cursor_to(x, y, duration=0.5, *, backend=None):
    """
    Move the cursor to a screen coordinate.

    duration is the movement time in seconds.
    This function does not click anything.
    """

    if not all(math.isfinite(value) for value in (x, y, duration)):
        raise ValueError("coordinates and duration must be finite")
    if duration < 0:
        raise ValueError("duration cannot be negative")

    if backend is None:
        import pyautogui as backend
    screen_width, screen_height = backend.size()

    if not (0 <= x < screen_width):
        raise ValueError("x is outside the screen")

    if not (0 <= y < screen_height):
        raise ValueError("y is outside the screen")

    backend.moveTo(
        x,
        y,
        duration=duration,
        tween=backend.easeInOutQuad
    )


# ------------------------------------------
# 6. Demonstration
# ------------------------------------------

if __name__ == "__main__":

    start = (100, 100)
    control1 = (150, 80)
    control2 = (200, 180)
    end = (300, 150)

    path = generate_bezier_path(
        start,
        control1,
        control2,
        end,
        steps=50
    )

    print("Number of points:", len(path))
    print("First point:", path[0])
    print("Middle point:", path[len(path) // 2])
    print("Last point:", path[-1])

    validate_path(path, start, end)

    print("Path validation passed.")
