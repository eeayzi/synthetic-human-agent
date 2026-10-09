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

class TestMoveCursorTo(unittest.TestCase):

    @patch("stealth_mouse.pyautogui.moveTo")
    @patch("stealth_mouse.pyautogui.size", return_value=(1000, 800))
    def test_valid_target(self, mock_size, mock_move):
        move_cursor_to(300, 200, duration=0.5)

        mock_move.assert_called_once_with(
            300, 200,
            duration=0.5,
            tween=__import__("pyautogui").easeInOutQuad
        )

    @patch("stealth_mouse.pyautogui.moveTo")
    def test_negative_duration(self, mock_move):
        with self.assertRaises(ValueError):
            move_cursor_to(300, 200, duration=-1)

        mock_move.assert_not_called()

    @patch("stealth_mouse.pyautogui.moveTo")
    @patch("stealth_mouse.pyautogui.size", return_value=(1000, 800))
    def test_x_outside_screen(self, mock_size, mock_move):
        with self.assertRaises(ValueError):
            move_cursor_to(1000, 200)

        mock_move.assert_not_called()

    @patch("stealth_mouse.pyautogui.moveTo")
    @patch("stealth_mouse.pyautogui.size", return_value=(1000, 800))
    def test_y_outside_screen(self, mock_size, mock_move):
        with self.assertRaises(ValueError):
            move_cursor_to(300, 800)

        mock_move.assert_not_called()


if __name__ == "__main__":
    test_bezier_endpoints()
    test_path_length()
    test_middle_point()
    test_distance()
    test_path_validation()
    test_invalid_t()

    print("All six test checks passed.")
