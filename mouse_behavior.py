"""Preserves the original curved cursor paths with guarded, cancellable steps."""
import math
from stealth_mouse import generate_bezier_path, distance_between, validate_path


def move_mouse_human(ui, x, y, control):
    ui.guard()
    position = ui.desktop.input.position()
    start = (position[0], position[1])
    end = (x, y)
    distance = distance_between(start, end)
    if distance == 0:
        return
    dx, dy = x-start[0], y-start[1]
    normal = (-dy/distance, dx/distance)
    offset1, offset2 = (control.rng.uniform(-.25, .25)*distance for _ in range(2))
    c1 = (start[0]+dx*.3+normal[0]*offset1, start[1]+dy*.3+normal[1]*offset1)
    c2 = (start[0]+dx*.7+normal[0]*offset2, start[1]+dy*.7+normal[1]*offset2)
    steps = min(max(int(distance/12), 20), 80)
    path = generate_bezier_path(start, c1, c2, end, steps)
    validate_path(path, start, end)
    width, height = ui.desktop.input.size()
    duration = (.3 + distance/2000)*control.rng.uniform(.8, 1.3)
    weights = [1.6-math.sin(math.pi*i/steps) for i in range(steps+1)]
    for (px, py), weight in zip(path, weights):
        ui.move_to(min(max(px, 3), width-4), min(max(py, 3), height-4))
        control.pause(duration*weight/sum(weights))
    control.audit.emit('mouse_moved', backend='pyautogui', distance_pixels=distance,
                       sampled_duration_seconds=duration, path_points=len(path))


def human_scroll(ui, clicks, control, page=None):
    if isinstance(clicks, bool) or not isinstance(clicks, int):
        raise ValueError('Scroll amount must be integer wheel clicks')
    
    # 1 click = 100 CSS pixels
    PIXELS_PER_CLICK = 100
    
    # INVERTED SIGN: 
    # Since up = True (positive clicks) scrolls DOWN on your system, 
    # we map a positive 'clicks' to a positive 'pixel_delta' to scroll down.
    sign, remaining = (-1 if clicks < 0 else 1), abs(clicks)
    
    while remaining:
        chunk = min(remaining, control.rng.randint(1, 3))
        pixel_delta = sign * chunk * PIXELS_PER_CLICK
        
        if page is not None:
            try:
                # scrollBy(top: pixel_delta)
                # If pixel_delta is positive, it scrolls down in CSS pixels.
                page.evaluate(f"window.scrollBy({{top: {pixel_delta}, behavior: 'smooth'}})")
            except Exception:
                ui.scroll(sign * chunk)
        else:
            ui.scroll(sign * chunk)
            
        control.audit.emit(
            'wheel_scrolled', 
            backend='playwright_eval' if page else 'pyautogui', 
            wheel_clicks=sign * chunk,
            pixels_scrolled=pixel_delta
        )
        
        remaining -= chunk
        control.pause(control.rng.uniform(.1, .25))