# # """Original-style visible browsing: OS keyboard, curved cursor, wheel and clicks.
# # Playwright launches the owned browser and inspects/verifies its DOM; it does not
# # replace the keyboard, mouse, or click actions in this adapter.
# # """
# # from mouse_behavior import move_mouse_human, human_scroll
# # from desktop import FocusLost
# #
# #
# # class WebAgent:
# #     def __init__(self, desktop, control, marker):
# #         self.desktop, self.control = desktop, control
# #         self.marker = marker
# #         self.manager = self.browser = self.context = self.page = None
# #         self.ui = None
# #
# #     def open(self):
# #         from playwright.sync_api import sync_playwright
# #         self.control.check()
# #         self.manager = sync_playwright().start()
# #         try:
# #             self.browser = self.manager.chromium.launch(headless=False, timeout=self.control.timeout_ms(),
# #                          args=['--window-position=0,0', '--start-maximized'])
# #             self.context = self.browser.new_context(no_viewport=True, accept_downloads=False, service_workers='block')
# #             # allowed = {self.origin+'/brief', self.origin+'/reference'}
# #             # def route_request(route):
# #             #     if route.request.url in allowed:
# #             #         route.continue_()
# #             #     else:
# #             #         self.control.audit.emit('network_request_blocked', backend='playwright_route')
# #             #         route.abort()
# #             # self.context.route('**/*', route_request)
# #             self.context.add_init_script(
# #                 'document.addEventListener("mousemove", e => {window.__trainingPointer={x:e.clientX,y:e.clientY};}, true)')
# #             self.page = self.context.new_page()
# #             self.page.set_content(f'<title>{self.marker}</title><p>Synthetic session starting</p>',
# #                                   timeout=self.control.timeout_ms())
# #             # Wait for the OS window title to reflect the owned page marker.
# #             hwnd = None
# #             for _ in range(30):
# #                 try:
# #                     hwnd = self.desktop.find_window(self.marker)
# #                     break
# #                 except FocusLost:
# #                     self.control.pause(.1)
# #             if hwnd is None:
# #                 raise FocusLost('Owned browser window did not appear')
# #             self.desktop.activate(hwnd, self.control)
# #             self.ui = self.desktop.owned_input(hwnd, self.control)
# #             self.control.audit.emit('browser_opened', backend='playwright_setup', observed_pid=self.ui.pid,
# #                                     window_handle=int(hwnd), input_backend='pyautogui')
# #             self._check_scale()
# #         except BaseException:
# #             self.close()
# #             raise
# #
# #     def _check_scale(self):
# #         info = self.page.evaluate('({ratio:devicePixelRatio, zoom:visualViewport.scale, x:screenX, y:screenY})')
# #         if abs(info['ratio']-1) > .01 or abs(info['zoom']-1) > .01 or info['x'] < -20 or info['y'] < -20:
# #             raise RuntimeError('Demo requires primary monitor, 100% Windows display scaling and 100% browser zoom')
# #
# #     def activate(self):
# #         self.desktop.activate(self.ui.hwnd, self.control)
# #         self._check_scale()
# #         self.ui.guard()
# #
# #     # def navigate(self, name):
# #     #     self.activate()
# #     #     url = self.origin+'/'+name
# #     #     if name not in ('brief', 'reference'):
# #     #         raise ValueError('Only configured local pages are allowed')
# #     #     self.ui.hotkey('ctrl', 'l')
# #     #     self.control.pause(0.1)
# #     #     for char in url:
# #     #         self.ui.write(char)
# #     #         self.control.pause(self.control.rng.uniform(.03, .10))
# #     #     self.ui.press('enter')
# #     #     self.page.wait_for_url(url, timeout=self.control.timeout_ms(), wait_until='domcontentloaded')
# #     #     if self.marker not in self.page.title():
# #     #         raise RuntimeError('Browser navigated outside the owned fixture')
# #     #     self.control.audit.emit('navigation_verified', backend='pyautogui', page=name, url=url)
# #
# #     def navigate(self, url):
# #         self.activate()
# #         self.control.audit.emit('navigation_started', url=url)
# #         self.ui.hotkey('ctrl', 'l')
# #         self.control.pause(0.1)
# #         for char in url:
# #             self.ui.write(char)
# #             self.control.pause(self.control.rng.uniform(.03, .10))
# #         self.ui.press('enter')
# #         self.page.wait_for_load_state('networkidle', timeout=self.control.timeout_ms())
# #         self.control.audit.emit('navigation_verified', backend='pyautogui', url=self.page.url)
# #
# #     def screen_point(self, x, y):
# #         self._check_scale()
# #         window = self.page.evaluate('''() => ({
# #             left:screenX+(outerWidth-innerWidth)/2,
# #             top:screenY+(outerHeight-innerHeight)-(outerWidth-innerWidth)/2,
# #             width:innerWidth, height:innerHeight})''')
# #         if not 0 <= x < window['width'] or not 0 <= y < window['height']:
# #             raise RuntimeError('DOM target is outside viewport')
# #         return window['left']+x, window['top']+y
# #
# #     # def click_reference_link(self):
# #     #     self.activate()
# #     #     box = self.page.locator('#next').bounding_box(timeout=self.control.timeout_ms())
# #     #     if not box:
# #     #         raise RuntimeError('Reference link not visible')
# #     #     x, y = self.screen_point(box['x']+box['width']*.5, box['y']+box['height']*.5)
# #     #     move_mouse_human(self.ui, x, y, self.control)
# #     #     self.control.pause(.15)
# #     #     pointer = self.page.evaluate('window.__trainingPointer || null')
# #     #     if pointer is None:
# #     #         raise RuntimeError('Could not observe the native pointer in the page; click aborted')
# #     #     desired_x, desired_y = box['x']+box['width']*.5, box['y']+box['height']*.5
# #     #     dx, dy = desired_x-pointer['x'], desired_y-pointer['y']
# #     #     if abs(dx) > 40 or abs(dy) > 40:
# #     #         raise RuntimeError('Screen/viewport calibration mismatch; click aborted')
# #     #     if abs(dx) > 2 or abs(dy) > 2:
# #     #         move_mouse_human(self.ui, x+dx, y+dy, self.control)
# #     #         self.control.pause(.15)
# #     #     over_link = self.page.evaluate("() => { const p=window.__trainingPointer; return !!p && !!document.elementFromPoint(p.x,p.y)?.closest('#next'); }")
# #     #     if not over_link:
# #     #         raise RuntimeError('Native pointer is not over the reference link; click aborted')
# #     #     self.ui.click()
# #     #     self.page.wait_for_url(self.origin+'/reference', timeout=self.control.timeout_ms(), wait_until='domcontentloaded')
# #     #     self.control.audit.emit('link_click_verified', backend='pyautogui', page='reference')
# #
# #     # def browse_until(self, target):
# #     #     self.activate()
# #     #     while self.control.clock() < target-12:
# #     #         self.ui.guard()
# #     #         viewport = self.page.evaluate('({width:innerWidth,height:innerHeight})')
# #     #         x, y = self.screen_point(viewport['width']*self.control.rng.uniform(.35,.65),
# #     #                                  viewport['height']*self.control.rng.uniform(.4,.7))
# #     #         move_mouse_human(self.ui, x, y, self.control)
# #     #         top = self.page.evaluate('scrollY')
# #     #         bottom = self.page.evaluate('scrollY+innerHeight >= document.documentElement.scrollHeight-5')
# #     #         up = bottom or (top > 0 and self.control.rng.random() < .15)
# #     #         human_scroll(self.ui, (1 if up else -1)*self.control.rng.randint(1,5), self.control)
# #     #         self.control.pause(self.control.rng.uniform(2, 5))
# #     #     self.control.idle_until(target, 'reading_browser', guard=self.ui.guard)
# #
# #     # In web_agent.py, replace the existing browse_until method with this one.
# #
# #     def browse_until(self, target):
# #         self.activate()
# #         while self.control.clock() < target - 15:  # Leave time for a final reading pause
# #             try:
# #                 # === PRE-ACTION CHECKS ===
# #                 self.ui.guard()  # Check if we still own the foreground window
# #                 if self.page.is_closed():
# #                     raise RuntimeError("Page was closed unexpectedly")
# #                 # Wait for the page to be stable before deciding what to do
# #                 self.page.wait_for_load_state('networkidle', timeout=5000)
# #                 self.page.locator('body').wait_for(timeout=5000)
# #
# #                 # === ACTION DECISION ===
# #                 # Decide whether to scroll or attempt to click a link
# #                 if self.control.rng.random() < 0.25:  # 25% chance to click a link
# #                     # Find all visible links on the page
# #                     links = self.page.locator('a:visible').all()
# #                     valid_links = [
# #                         link for link in links
# #                         if
# #                         link.get_attribute('href') and not link.get_attribute('href').startswith(('#', 'javascript:'))
# #                     ]
# #
# #                     if valid_links:
# #                         target_link = self.control.rng.choice(valid_links)
# #                         self.control.audit.emit('link_interaction_started', text=target_link.inner_text()[:80])
# #
# #                         box = target_link.bounding_box()
# #                         if box and box['width'] > 0 and box['height'] > 0:
# #                             # Use the robust clicking logic
# #                             x, y = self.screen_point(box['x'] + box['width'] * 0.5, box['y'] + box['height'] * 0.5)
# #                             move_mouse_human(self.ui, x, y, self.control)
# #                             self.ui.click()
# #
# #                             # IMPORTANT: Pause briefly after a click to let navigation start
# #                             self.control.pause(1.5)
# #                             continue  # Immediately restart the loop to re-evaluate the new page state
# #
# #                 # === DEFAULT SCROLL ACTION ===
# #                 # If we didn't click, we scroll
# #                 viewport = self.page.evaluate('({width:innerWidth,height:innerHeight})')
# #                 x, y = self.screen_point(viewport['width'] * self.control.rng.uniform(.35, .65),
# #                                          viewport['height'] * self.control.rng.uniform(.4, .7))
# #                 move_mouse_human(self.ui, x, y, self.control)
# #
# #                 top = self.page.evaluate('scrollY')
# #                 bottom = self.page.evaluate('scrollY+innerHeight >= document.documentElement.scrollHeight-5')
# #                 up = bottom or (top > 0 and self.control.rng.random() < .15)
# #
# #                 human_scroll(self.ui, (1 if up else -1) * self.control.rng.randint(25, 60), self.control)
# #                 self.control.pause(self.control.rng.uniform(1, 3))
# #
# #             except Exception as e:
# #                 self.control.audit.emit('browse_action_failed', error=str(e))
# #                 # If an error occurs (like a page closing), pause and try to recover on the next loop
# #                 self.control.pause(2.0)
# #
# #         self.control.idle_until(target, 'reading_browser_final', guard=self.ui.guard)
# #
# #     def close(self):
# #         errors = []
# #         if self.browser is not None:
# #             try:
# #                 self.browser.close()
# #             except Exception as exc:
# #                 errors.append(type(exc).__name__)
# #             self.browser = None
# #         if self.manager is not None:
# #             try:
# #                 self.manager.stop()
# #             except Exception as exc:
# #                 errors.append(type(exc).__name__)
# #             self.manager = None
# #         self.control.audit.emit('browser_cleanup', errors=errors)
# #         if errors:
# #             raise RuntimeError('Browser cleanup failed: '+', '.join(errors))
#
# # In web_agent.py, replace the whole file with this:
#
# from playwright.sync_api import sync_playwright
# from playwright_stealth import Stealth # <-- This is the simple, correct import based on your __init__.py
# from mouse_behavior import move_mouse_human, human_scroll
# from desktop import FocusLost
# import time
#
#
# class WebAgent:
#     def __init__(self, desktop, control, marker):
#         self.desktop, self.control = desktop, control
#         self.marker = marker
#         self.manager = self.browser = self.context = self.page = None
#         self.ui = None
#
#     def open(self):
#         from playwright.sync_api import sync_playwright
#         from playwright_stealth import Stealth
#
#         self.control.check()
#         try:
#             self.manager = sync_playwright().start()
#             self.browser = self.manager.chromium.launch(headless=False, timeout=self.control.timeout_ms())
#
#             self.context = self.browser.new_context(
#                 user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
#                 viewport={'width': 1920, 'height': 1080},
#                 locale='en-SG',
#                 timezone_id='Asia/Singapore',
#                 accept_downloads=False
#             )
#
#             # --- THE NUCLEAR OPTION: OVERRIDE PERMISSIONS STATE ---
#             # This script runs before any other page script. It spoofs the permissions API
#             # to make it look like a normal user's browser.
#             permissions_script = """
#                 const originalQuery = window.navigator.permissions.query;
#                 window.navigator.permissions.query = (parameters) => (
#                     parameters.name === 'notifications' ?
#                     Promise.resolve({ state: Notification.permission }) :
#                     originalQuery(parameters)
#                 );
#             """
#             self.context.add_init_script(permissions_script)
#
#             # Apply the main stealth library after our custom script
#             stealth_object = Stealth()
#             stealth_object.apply_stealth_sync(self.context)
#
#             # The rest of the startup sequence remains the same
#             self.page = self.context.new_page()
#             self.page.goto('about:blank', wait_until='networkidle')
#             self.page.evaluate(f"document.title = '{self.marker}'")
#             self.control.pause(0.5)
#
#             hwnd = self.desktop.find_window(self.marker)
#
#             self.desktop.activate(hwnd, self.control)
#             self.ui = self.desktop.owned_input(hwnd, self.control)
#             self.control.audit.emit('browser_opened', backend='playwright_stealth_permissions_override',
#                                     observed_pid=self.ui.pid,
#                                     window_handle=int(hwnd), input_backend='pyautogui')
#             self._check_scale()
#
#             self.context.on('page', self._handle_new_page)
#
#         except BaseException:
#             self.close()
#             raise
#
#     def _handle_new_page(self, new_page):
#         # When a new tab opens, update self.page to control the new one
#         self.control.audit.emit('new_tab_detected', url=new_page.url)
#         self.page = new_page
#         # You may need to activate the new window if focus doesn't switch automatically
#         self.desktop.activate(self.ui.hwnd, self.control)
#
#     def _handle_popups(self):
#         # --- FEATURE 3: HANDLE POP-UPS ---
#         # A simple and fast way to deal with common cookie banners.
#         # It looks for common "accept" texts and clicks them if found.
#         try:
#             # More generic selector for buttons/links containing acceptance text
#             accept_button = self.page.locator(
#                 '*:visible:has-text-matches("(Accept|Agree|Allow|OK|Got it|I understand|Consent)", "i")'
#             ).last()
#             if accept_button.is_visible(timeout=1000):
#                 self.control.audit.emit('popup_handler_started', text=accept_button.inner_text()[:50])
#                 accept_button.click(timeout=2000)
#                 self.control.pause(1.0)  # Pause for the banner to disappear
#         except Exception:
#             # It's okay if no pop-up is found, just continue.
#             pass
#
#     # The rest of the file remains largely the same, but with pop-up handling added.
#     def navigate(self, url):
#         self.activate()
#         self.control.audit.emit('navigation_started', url=url)
#         self.ui.hotkey('ctrl', 'l')
#         self.control.pause(0.1)
#         for char in url:
#             self.ui.write(char)
#             self.control.pause(self.control.rng.uniform(.03, .10))
#         self.ui.press('enter')
#         self.page.wait_for_load_state('networkidle', timeout=self.control.timeout_ms())
#         self._handle_popups()  # Handle pop-ups after navigation
#         self.control.audit.emit('navigation_verified', backend='pyautogui', url=self.page.url)
#
#     # def browse_until(self, target):
#     #     self.activate()
#     #     while self.control.clock() < target - 15:
#     #         try:
#     #             self.ui.guard()
#     #             if self.page.is_closed():
#     #                 # If a link opened a new tab and closed the old one, our context might have updated.
#     #                 # Let's try to use the latest page from the context.
#     #                 if self.context.pages:
#     #                     self.page = self.context.pages[-1]
#     #                     self.control.audit.emit('recovered_from_closed_page')
#     #                 else:
#     #                     raise RuntimeError("Page was closed and no new page is available")
#     #
#     #             # Wait for the page to be generally stable before we do anything.
#     #             self.page.wait_for_load_state('networkidle', timeout=5000)
#     #             self._handle_popups()
#     #
#     #             # --- ACTION DECISION ---
#     #             if self.control.rng.random() < 0.3:  # 30% chance to click a link
#     #                 links = self.page.locator('a:visible').all()
#     #                 valid_links = [
#     #                     link for link in links
#     #                     if
#     #                     link.get_attribute('href') and not link.get_attribute('href').startswith(('#', 'javascript:'))
#     #                 ]
#     #
#     #                 if valid_links:
#     #                     target_link = self.control.rng.choice(valid_links)
#     #                     self.control.audit.emit('link_interaction_started', text=target_link.inner_text()[:80])
#     #
#     #                     box = target_link.bounding_box()
#     #                     if box and box['width'] > 0 and box['height'] > 0:
#     #                         x, y = self.screen_point(box['x'] + box['width'] * 0.5, box['y'] + box['height'] * 0.5)
#     #
#     #                         # --- THE BULLETPROOF NAVIGATION PATTERN ---
#     #                         # 1. Start waiting for the navigation event BEFORE you click.
#     #                         move_mouse_human(self.ui, x, y, self.control)
#     #                         with self.page.expect_navigation(wait_until='networkidle', timeout=10000):
#     #                             # 2. Perform the click that triggers the navigation.
#     #                             target_link.click(timeout=5000)
#     #
#     #                         # 3. When this block finishes, the new page is fully loaded and ready.
#     #                         self.control.audit.emit('navigation_after_click_success')
#     #                         continue  # Restart the loop to evaluate the new page.
#     #
#     #             # --- DEFAULT SCROLL ACTION ---
#     #             viewport = self.page.evaluate('({width:innerWidth,height:innerHeight})')
#     #             x_pos, y_pos = self.screen_point(viewport['width'] * self.control.rng.uniform(.35, .65),
#     #                                              viewport['height'] * self.control.rng.uniform(.4, .7))
#     #             move_mouse_human(self.ui, x_pos, y_pos, self.control)
#     #             top = self.page.evaluate('scrollY')
#     #             bottom = self.page.evaluate('scrollY+innerHeight >= document.documentElement.scrollHeight-5')
#     #             up = bottom or (top > 0 and self.control.rng.random() < .15)
#     #             human_scroll(self.ui, (1 if up else -1) * self.control.rng.randint(25, 60), self.control)
#     #             self.control.pause(self.control.rng.uniform(1, 3))
#     #
#     #         except Exception as e:
#     #             self.control.audit.emit('browse_action_failed', error=str(e))
#     #             self.control.pause(2.0)
#     #             # If a page fails to load, try navigating to the main site again to recover.
#     #             try:
#     #                 self.navigate("https://www.coursera.org/")
#     #             except Exception as nav_exc:
#     #                 self.control.audit.emit('recovery_nav_failed', error=str(nav_exc))
#     #
#     #     self.control.idle_until(target, 'reading_browser_final', guard=self.ui.guard)
#
#
#     def browse_until(self, target):
#         # self.activate()
#         # self.control.audit.emit('browsing_started', mode='paranoid_live', end_time=target)
#         #
#         # while self.control.clock() < target - 5:  # Leave time for a final reading pause
#         #     try:
#         #         # --- STAGE 1: Pre-Action Validation ---
#         #         # At the start of every single loop, we re-verify everything.
#         #         self.ui.guard()
#         #         if self.page.is_closed():
#         #             if not self.context.pages: raise RuntimeError("Page closed and no other pages available")
#         #             self.page = self.context.pages[-1]  # Recover to the newest page if one exists
#         #             self.control.audit.emit('recovered_from_closed_page')
#         #             self.page.bring_to_front()
#         #
#         #         # Wait for the page to be stable before doing anything. This is CRITICAL.
#         #         self.page.wait_for_load_state('networkidle', timeout=7000)
#         #
#         #         # --- STAGE 2: Mouse Movement ---
#         #         # Move the mouse, but assume the page could have changed.
#         #         self.ui.guard()  # Check focus again right before moving
#         #         viewport = self.page.evaluate('({width:innerWidth,height:innerHeight})')
#         #         x_pos, y_pos = self.screen_point(
#         #             viewport['width'] * self.control.rng.uniform(.35, .65),
#         #             viewport['height'] * self.control.rng.uniform(.4, .7)
#         #         )
#         #         move_mouse_human(self.ui, x_pos, y_pos, self.control)
#         #
#         #         # --- STAGE 3: Scroll Action ---
#         #         # Re-validate the page AGAIN before scrolling.
#         #         self.ui.guard()
#         #         if self.page.is_closed(): continue  # If closed, restart the loop
#         #
#         #         # Get scroll info, but wrap in a try/except in case the page reloaded mid-mouse-move
#         #         try:
#         #             top = self.page.evaluate('scrollY')
#         #             bottom = self.page.evaluate('scrollY+innerHeight >= document.documentElement.scrollHeight-5')
#         #         except Exception:
#         #             self.control.audit.emit('scroll_info_failed_retrying')
#         #             continue  # If evaluate fails, restart the loop to re-validate
#         #
#         #         up = bottom or (top > 0 and self.control.rng.random() < .15)
#         #         human_scroll(self.ui, (1 if up else -1) * self.control.rng.randint(25, 60), self.control)
#         #
#         #         # --- STAGE 4: Pause and Breathe ---
#         #         # Finally, pause to simulate reading.
#         #         self.control.pause(self.control.rng.uniform(3, 6))
#         #
#         #     except Exception as e:
#         #         # This is our global error handler for the loop.
#         #         self.control.audit.emit('browse_loop_error', error=str(e))
#         #         self.control.pause(3.0)  # A longer pause after an error
#         #         try:
#         #             # The most robust recovery is to try navigating to a simple, known-good site.
#         #             if not self.page.is_closed():
#         #                 self.page.goto("https://www.wikipedia.org/", wait_until='networkidle')
#         #         except Exception as recovery_exc:
#         #             self.control.audit.emit('browse_recovery_failed', error=str(recovery_exc))
#         #             break  # If we can't even recover, exit the loop to prevent spamming errors.
#         #
#         # self.control.idle_until(target, 'reading_browser_final', guard=self.ui.guard)
#             self.activate()
#             self.control.audit.emit('test_step_1_started', description='Looping with only guard and pause')
#
#             while self.control.clock() < target - 5:
#                 try:
#                     # 1. Check if the window is still in focus (this is a safe action)
#                     self.ui.guard()
#
#                     # 2. Just wait, simulating a user doing nothing
#                     self.control.pause(2.0)
#
#                 except Exception as e:
#                     self.control.audit.emit('test_step_1_FAILED', error=str(e))
#                     raise  # If this fails, something is fundamentally wrong
#
#             # If the loop completes without error, this part will run
#             self.control.idle_until(target, 'reading_browser_final', guard=self.ui.guard)
#             self.control.audit.emit('test_step_1_PASSED')
#
#     # The close, _check_scale, screen_point, and activate methods remain the same.
#     # Make sure they are still in your file.
#     def _check_scale(self):
#         info = self.page.evaluate('({ratio:devicePixelRatio, zoom:visualViewport.scale, x:screenX, y:screenY})')
#         if abs(info['ratio'] - 1) > .01 or abs(info['zoom'] - 1) > .01 or info['x'] < -20 or info['y'] < -20:
#             raise RuntimeError('Demo requires primary monitor, 100% Windows display scaling and 100% browser zoom')
#
#     def activate(self):
#         self.desktop.activate(self.ui.hwnd, self.control)
#         self._check_scale()
#         self.ui.guard()
#
#     def screen_point(self, x, y):
#         self._check_scale()
#         window = self.page.evaluate('''() => ({
#             left:screenX+(outerWidth-innerWidth)/2,
#             top:screenY+(outerHeight-innerHeight)-(outerWidth-innerWidth)/2,
#             width:innerWidth, height:innerHeight})''')
#         if not 0 <= x < window['width'] or not 0 <= y < window['height']:
#             raise RuntimeError('DOM target is outside viewport')
#         return window['left'] + x, window['top'] + y
#
#     def close(self):
#         errors = []
#         if self.browser is not None:
#             try:
#                 self.browser.close()
#             except Exception as exc:
#                 errors.append(f"browser_close: {type(exc).__name__}")
#             self.browser = None
#         if self.manager is not None:
#             try:
#                 self.manager.stop()
#             except Exception as exc:
#                 errors.append(f"manager_stop: {type(exc).__name__}")
#             self.manager = None
#         self.control.audit.emit('browser_cleanup', errors=errors)
#         if errors:
#             raise RuntimeError('Browser cleanup failed: '+', '.join(errors))

# In web_agent.py, replace the ENTIRE file with this new code.

import pyautogui
import time
import os
import subprocess
from mouse_behavior import move_mouse_human, human_scroll
from desktop import FocusLost


class WebAgent:
    def __init__(self, desktop, control, marker, config):
        self.desktop = desktop
        self.control = control
        self.marker = marker  # We can still use this to find the window
        self.config = config
        self.process = None
        self.ui = None

    def open(self):
        """Launches Chrome using a pure subprocess call."""
        self.control.check()
        profile_path = os.path.join(os.getcwd(), 'chrome-profile-gui')
        chrome_command = [
            'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
            '--start-maximized',
            f'--user-data-dir={profile_path}'
        ]

        self.process = subprocess.Popen(chrome_command)
        self.control.audit.emit('browser_launched_gui', pid=self.process.pid)
        self.control.pause(3.0)  # Wait for browser to open

        # We can't set the title directly, so we find the window by class name.
        # This is less specific, so we assume only one Chrome window is open.
        hwnd = self.desktop.gui.FindWindow("Chrome_WidgetWin_1", None)
        if not hwnd:
            raise RuntimeError("Could not find the Chrome window after launching.")

        self.desktop.activate(hwnd, self.control)
        self.ui = self.desktop.owned_input(hwnd, self.control)
        self.control.audit.emit('browser_opened', backend='pyautogui', observed_pid=self.ui.pid,
                                window_handle=int(hwnd))

    def navigate(self, url):
        """Navigates by typing into the address bar with PyAutoGUI."""
        self.activate()
        self.control.audit.emit('navigation_started_gui', url=url)
        self.ui.hotkey('ctrl', 'l')
        self.control.pause(0.2)
        self.ui.write(url)
        self.control.pause(0.1)
        self.ui.press('enter')
        self.control.pause(5.0)  # Give page time to load
        self.control.audit.emit('navigation_finished_gui', url=url)

    def find_and_click_link(self):
        """Finds a link using image recognition relative to an anchor."""
        self.activate()
        # In a real scenario, you'd loop through your anchor images.
        # For this example, we'll assume we are on Coursera.
        anchor_image = self.config['anchor_images']['coursera']

        try:
            self.control.audit.emit('image_search_started', image=anchor_image)
            anchor_location = pyautogui.locateOnScreen(anchor_image, confidence=0.8)

            if anchor_location:
                self.control.audit.emit('image_search_succeeded', image=anchor_image, location=str(anchor_location))
                # From the anchor, move to a relative position to click a link
                # (e.g., a "Programs" or "Explore" tab).
                # These offsets would need to be found by hand for each site.
                anchor_center = pyautogui.center(anchor_location)
                target_x = anchor_center.x + 200  # Move 200 pixels to the right
                target_y = anchor_center.y + 5  # Stay at roughly the same height

                move_mouse_human(self.ui, target_x, target_y, self.control)
                self.ui.click()
                self.control.pause(5.0)  # Wait for new page to load
                return True
            else:
                self.control.audit.emit('image_search_failed', image=anchor_image)
                return False
        except pyautogui.PyAutoGUIException as e:
            # This happens if the image file isn't found
            self.control.audit.emit('image_search_error', error=str(e))
            return False

    def browse_until(self, target):
        self.activate()
        self.control.audit.emit('browsing_started_gui')

        while self.control.clock() < target - 10:
            self.ui.guard()

            # Simple behavior: scroll for a bit
            human_scroll(self.ui, self.control.rng.randint(-60, 60), self.control)
            self.control.pause(self.control.rng.uniform(2, 5))

            # Add a chance to try and click a link
            if self.control.rng.random() < 0.2:
                self.find_and_click_link()

    def close(self):
        """Closes the browser by sending Alt+F4."""
        if self.ui:
            try:
                self.activate()
                self.ui.hotkey('alt', 'f4')
            except Exception as e:
                self.control.audit.emit('browser_close_failed_gui', error=str(e))
        if self.process:
            try:
                self.process.terminate()  # Fallback to ensure it closes
            except Exception:
                pass
        self.control.audit.emit('browser_cleanup_gui')

    # You will need to add _check_scale and activate methods to this class.
    def _check_scale(self):
        # With PyAutoGUI, we can't easily check browser zoom, but we can check screen size.
        # This is mostly a placeholder now.
        pass

    def activate(self):
        if self.ui:
            self.desktop.activate(self.ui.hwnd, self.control)
            self.ui.guard()
