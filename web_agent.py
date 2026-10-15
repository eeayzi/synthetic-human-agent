"""Original-style visible browsing: OS keyboard, curved cursor, wheel and clicks.
Playwright launches the owned browser and inspects/verifies its DOM; it does not
replace the keyboard, mouse, or click actions in this adapter.
"""
from mouse_behavior import move_mouse_human, human_scroll
from desktop import FocusLost


class WebAgent:
    def __init__(self, desktop, control, origin, marker):
        self.desktop, self.control = desktop, control
        self.origin, self.marker = origin, marker
        self.manager = self.browser = self.context = self.page = None
        self.ui = None

    def open(self):
        from playwright.sync_api import sync_playwright
        self.control.check()
        self.manager = sync_playwright().start()
        try:
            self.browser = self.manager.chromium.launch(headless=False, timeout=self.control.timeout_ms(),
                         args=['--window-position=0,0', '--start-maximized'])
            self.context = self.browser.new_context(no_viewport=True, accept_downloads=False, service_workers='block')
            allowed = {self.origin+'/brief', self.origin+'/reference'}
            def route_request(route):
                if route.request.url in allowed:
                    route.continue_()
                else:
                    self.control.audit.emit('network_request_blocked', backend='playwright_route')
                    route.abort()
            self.context.route('**/*', route_request)
            self.context.add_init_script(
                'document.addEventListener("mousemove", e => {window.__trainingPointer={x:e.clientX,y:e.clientY};}, true)')
            self.page = self.context.new_page()
            self.page.set_content(f'<title>{self.marker}</title><p>Synthetic session starting</p>',
                                  timeout=self.control.timeout_ms())
            # Wait for the OS window title to reflect the owned page marker.
            hwnd = None
            for _ in range(30):
                try:
                    hwnd = self.desktop.find_window(self.marker)
                    break
                except FocusLost:
                    self.control.pause(.1)
            if hwnd is None:
                raise FocusLost('Owned browser window did not appear')
            self.desktop.activate(hwnd, self.control)
            self.ui = self.desktop.owned_input(hwnd, self.control)
            self.control.audit.emit('browser_opened', backend='playwright_setup', observed_pid=self.ui.pid,
                                    window_handle=int(hwnd), input_backend='pyautogui')
            self._check_scale()
        except BaseException:
            self.close()
            raise

    def _check_scale(self):
        info = self.page.evaluate('({ratio:devicePixelRatio, zoom:visualViewport.scale, x:screenX, y:screenY})')
        if abs(info['ratio']-1) > .01 or abs(info['zoom']-1) > .01 or info['x'] < -20 or info['y'] < -20:
            raise RuntimeError('Demo requires primary monitor, 100% Windows display scaling and 100% browser zoom')

    def activate(self):
        self.desktop.activate(self.ui.hwnd, self.control)
        self._check_scale()
        self.ui.guard()

    def navigate(self, name):
        self.activate()
        url = self.origin+'/'+name
        if name not in ('brief', 'reference'):
            raise ValueError('Only configured local pages are allowed')
        self.ui.hotkey('ctrl', 'l')
        for char in url:
            self.ui.write(char)
            self.control.pause(self.control.rng.uniform(.03, .10))
        self.ui.press('enter')
        self.page.wait_for_url(url, timeout=self.control.timeout_ms(), wait_until='domcontentloaded')
        if self.marker not in self.page.title():
            raise RuntimeError('Browser navigated outside the owned fixture')
        self.control.audit.emit('navigation_verified', backend='pyautogui', page=name, url=url)

    def screen_point(self, x, y):
        self._check_scale()
        window = self.page.evaluate('''() => ({
            left:screenX+(outerWidth-innerWidth)/2,
            top:screenY+(outerHeight-innerHeight)-(outerWidth-innerWidth)/2,
            width:innerWidth, height:innerHeight})''')
        if not 0 <= x < window['width'] or not 0 <= y < window['height']:
            raise RuntimeError('DOM target is outside viewport')
        return window['left']+x, window['top']+y

    def click_reference_link(self):
        self.activate()
        box = self.page.locator('#next').bounding_box(timeout=self.control.timeout_ms())
        if not box:
            raise RuntimeError('Reference link not visible')
        x, y = self.screen_point(box['x']+box['width']*.5, box['y']+box['height']*.5)
        move_mouse_human(self.ui, x, y, self.control)
        self.control.pause(.15)
        pointer = self.page.evaluate('window.__trainingPointer || null')
        if pointer is None:
            raise RuntimeError('Could not observe the native pointer in the page; click aborted')
        desired_x, desired_y = box['x']+box['width']*.5, box['y']+box['height']*.5
        dx, dy = desired_x-pointer['x'], desired_y-pointer['y']
        if abs(dx) > 40 or abs(dy) > 40:
            raise RuntimeError('Screen/viewport calibration mismatch; click aborted')
        if abs(dx) > 2 or abs(dy) > 2:
            move_mouse_human(self.ui, x+dx, y+dy, self.control)
            self.control.pause(.15)
        over_link = self.page.evaluate("() => { const p=window.__trainingPointer; return !!p && !!document.elementFromPoint(p.x,p.y)?.closest('#next'); }")
        if not over_link:
            raise RuntimeError('Native pointer is not over the reference link; click aborted')
        self.ui.click()
        self.page.wait_for_url(self.origin+'/reference', timeout=self.control.timeout_ms(), wait_until='domcontentloaded')
        self.control.audit.emit('link_click_verified', backend='pyautogui', page='reference')

    def browse_until(self, target):
        self.activate()
        while self.control.clock() < target-12:
            self.ui.guard()
            viewport = self.page.evaluate('({width:innerWidth,height:innerHeight})')
            x, y = self.screen_point(viewport['width']*self.control.rng.uniform(.35,.65),
                                     viewport['height']*self.control.rng.uniform(.4,.7))
            move_mouse_human(self.ui, x, y, self.control)
            top = self.page.evaluate('scrollY')
            bottom = self.page.evaluate('scrollY+innerHeight >= document.documentElement.scrollHeight-5')
            up = bottom or (top > 0 and self.control.rng.random() < .15)
            human_scroll(self.ui, (1 if up else -1)*self.control.rng.randint(1,5), self.control)
            self.control.pause(self.control.rng.uniform(2, 5))
        self.control.idle_until(target, 'reading_browser', guard=self.ui.guard)

    def close(self):
        errors = []
        if self.browser is not None:
            try:
                self.browser.close()
            except Exception as exc:
                errors.append(type(exc).__name__)
            self.browser = None
        if self.manager is not None:
            try:
                self.manager.stop()
            except Exception as exc:
                errors.append(type(exc).__name__)
            self.manager = None
        self.control.audit.emit('browser_cleanup', errors=errors)
        if errors:
            raise RuntimeError('Browser cleanup failed: '+', '.join(errors))
