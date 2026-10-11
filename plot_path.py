import matplotlib.pyplot as plt

from stealth_mouse import generate_bezier_path

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

# Separate the x and y coordinates
x_values = [point[0] for point in path]
y_values = [point[1] for point in path]

# Draw the Bezier curve
plt.plot(x_values, y_values, label="Bezier curve")

# Draw the four control points
control_points = [
    start, control1, control2, end
]

cx = [point[0] for point in control_points]
cy = [point[1] for point in control_points]

plt.scatter(cx, cy, label="Control points")

# Connect the control points
plt.plot(cx, cy, "--", label="Control polygon")

plt.xlabel("X coordinate")
plt.ylabel("Y coordinate")
plt.title("Cubic Bezier Curve")
plt.legend()
plt.grid(True)
plt.axis("equal")
plt.show()
