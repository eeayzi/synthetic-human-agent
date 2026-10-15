import unittest

from unittest.mock import patch
from stealth_mouse import move_cursor_to
import math

from stealth_mouse import (
    bezier_point,
    generate_bezier_path,
    distance_between,
    validate_path,
)


def test_bezier_endpoints():
    p0 = (0, 0)
    p1 = (10, 20)
    p2 = (20, 20)
    p3 = (30, 0)

    assert bezier_point(p0, p1, p2, p3, 0) == p0
    assert bezier_point(p0, p1, p2, p3, 1) == p3


def test_path_length():
    points = generate_bezier_path(
        (0, 0),
        (10, 20),
        (20, 20),
        (30, 0),
        steps=20,
    )

    assert len(points) == 21


def test_middle_point():
    p0 = (0, 0)
    p1 = (10, 20)
    p2 = (20, 20)
    p3 = (30, 0)

    x, y = bezier_point(p0, p1, p2, p3, 0.5)

    assert math.isclose(x, 15.0)
    assert math.isclose(y, 15.0)


def test_distance():
    assert math.isclose(
        distance_between((0, 0), (3, 4)),
        5.0
    )


def test_path_validation():
    start = (0, 0)
    end = (30, 0)

    points = generate_bezier_path(
        start, (10, 20), (20, 20), end
    )

    assert validate_path(points, start, end) is True


def test_invalid_t():
    try:
        bezier_point(
            (0, 0), (10, 20), (20, 20), (30, 0), 1.5
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid t was not rejected")

class TestGeometry(unittest.TestCase):
    def test_geometry(self):
        test_bezier_endpoints()
        test_path_length()
        test_middle_point()
        test_distance()
        test_path_validation()
        test_invalid_t()

    def test_invalid_path_numbers(self):
        with self.assertRaises(ValueError):
            validate_path([(float("nan"), 0)], (0, 0), (0, 0))


class TestMoveCursorTo(unittest.TestCase):
    def test_valid_target(self):
        from unittest.mock import Mock
        backend = Mock()
        backend.size.return_value = (1000, 800)
        move_cursor_to(300, 200, duration=0.5, backend=backend)
        backend.moveTo.assert_called_once_with(
            300, 200, duration=0.5, tween=backend.easeInOutQuad)

    def test_invalid_target_never_moves(self):
        from unittest.mock import Mock
        for x, y, duration in [(1000, 200, .5), (300, 800, .5),
                                (300, 200, -1), (300, 200, float("nan")),
                                (float("inf"), 200, .5)]:
            backend = Mock()
            backend.size.return_value = (1000, 800)
            with self.subTest(x=x, y=y, duration=duration):
                with self.assertRaises(ValueError):
                    move_cursor_to(x, y, duration, backend=backend)
                backend.moveTo.assert_not_called()


if __name__ == "__main__":
    unittest.main()
