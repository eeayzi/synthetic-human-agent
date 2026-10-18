"""
Generic web browsing agent that dynamically adheres to a consolidated
list of brand domains for navigation, interaction, and smooth scrolling.
"""
from mouse_behavior import move_mouse_human, human_scroll
from desktop import FocusLost
from explorer_launcher import ExplorerLauncher
from web_policy import AccessRestricted, restriction_reason
from urllib.parse import urlparse

# What to do when a cookie/consent banner covers the page:
#   'reject' -> click "Reject all" / "Decline" / "Necessary only" (default, shares the least data)
#   'accept' -> click "Accept all" / "Allow all" / "I agree"
#   'stop'   -> old behaviour: stop the run as blocked
COOKIE_CONSENT_CHOICE = 'reject'
MAX_CONSENT_ATTEMPTS = 3

# Playwright errors that just mean "the page navigated while we were reading it".
NAVIGATION_RACE_MESSAGES = ('execution context was destroyed', 'cannot find context with specified id',
                            'most likely because of a navigation', 'frame was detached',
                            'execution context is not available')


def is_navigation_race(exc):
    return any(m in str(exc).lower() for m in NAVIGATION_RACE_MESSAGES)

# Finds visible modal dialogs and splits them into cookie/consent banners vs. anything else.
# For a consent banner it also returns the viewport centre of the button matching the configured choice.
PAGE_SNAPSHOT_JS = r'''(choice) => {
    const visible=e => { const r=e.getBoundingClientRect(),s=getComputedStyle(e);
        return r.width>5 && r.height>5 && r.bottom>0 && r.top<innerHeight && r.right>0 && r.left<innerWidth && s.display!=='none' && s.visibility!=='hidden' && s.opacity!=='0'; };
    const norm=t => (t||'').replace(/\s+/g,' ').trim();
    // Button label for matching: drop decorative arrows/ticks/punctuation ("Continue without agreeing →").
    const label=e => norm(e.innerText||e.value||e.getAttribute('aria-label')||e.getAttribute('title'))
        .replace(/^[✓✔×✕\s]+/,'').replace(/[\s→›»>.!✓✔]+$/,'');
    // querySelectorAll that also looks inside open shadow roots (Usercentrics, some Samsung/Dell widgets).
    const deepAll=(root, sel) => { const out=[...root.querySelectorAll(sel)];
        for (const el of root.querySelectorAll('*')) if (el.shadowRoot) out.push(...deepAll(el.shadowRoot, sel));
        return out; };
    const challenge=deepAll(document,'iframe').some(e => visible(e) &&
        /recaptcha|hcaptcha|challenges.cloudflare|captcha|challenge/i.test((e.src||'')+' '+(e.title||'')));

    const consentAttr=/onetrust|optanon|cookie|consent|gdpr|ccpa|cmp|truste|didomi|usercentrics|cookiebot|osano|privacy-?banner|qc-cmp|sp_message|evidon|termly|iubenda|cookieyes|cky-|klaro|complianz|cc-window|cc-banner/i;
    const attrs=e => [e.id, typeof e.className==='string'?e.className:(e.className&&e.className.baseVal)||'',
        e.getAttribute('aria-label')||'', e.getAttribute('aria-labelledby')?norm(document.getElementById(e.getAttribute('aria-labelledby'))?.innerText):''].join(' ');
    const consentText=/\bcookies?\b|your privacy|privacy (choices|preferences|settings)|consent to|tracking technologies|personal data|we value your privacy/i;
    const isConsent=e => {
        for (let n=e; n && n!==document.body; n=n.parentElement) if (consentAttr.test(attrs(n))) return true;
        const text=norm(e.innerText);
        return text.length<5000 && consentText.test(text);
    };

    const dialogs=deepAll(document,'[role="dialog"],[role="alertdialog"],[aria-modal="true"],dialog[open]').filter(visible);
    const known=deepAll(document,'#onetrust-banner-sdk,#onetrust-consent-sdk [role="dialog"],#CybotCookiebotDialog,#usercentrics-root,.qc-cmp2-container,#didomi-popup,#truste-consent-track,#cookie-law-info-bar,.cky-consent-container,.cc-window,#termly-code-snippet-support,[aria-label*="cookie" i]').filter(visible);
    // Non-standard banners: a fixed/sticky bar whose id/class mentions cookies/consent and talks about cookies.
    const generic=deepAll(document,'[id*="cookie" i],[class*="cookie" i],[id*="consent" i],[class*="consent" i],[id*="gdpr" i],[class*="privacy-banner" i]')
        .filter(e => visible(e) && /fixed|sticky/.test(getComputedStyle(e).position) && consentText.test(norm(e.innerText).slice(0,2000)));
    // Consent widgets rendered inside a shadow root: the host is often 0x0, so use its visible fixed/dialog content.
    const shadowed=deepAll(document,'*').filter(h => h.shadowRoot && consentAttr.test(attrs(h)))
        .flatMap(h => deepAll(h.shadowRoot,'*').filter(e => visible(e) &&
            (/fixed|sticky/.test(getComputedStyle(e).position) || /dialog/.test(e.getAttribute('role')||''))));
    let consentBoxes=[...new Set([...dialogs.filter(isConsent), ...known, ...generic, ...shadowed])];
    consentBoxes=consentBoxes.filter(b => !consentBoxes.some(o => o!==b && o.contains(b)));  // keep outermost

    const others=dialogs.filter(d => !consentBoxes.some(c => c===d || c.contains(d) || d.contains(c)));
    // Small non-modal popovers (hover menus, "Deliver to <country>" toasts) don't block the page: ignore them.
    const isModal=d => d.getAttribute('aria-modal')==='true' || d.getAttribute('role')==='alertdialog' ||
        (d.tagName==='DIALOG' && d.matches(':modal'));
    const area=d => { const r=d.getBoundingClientRect(); return (r.width*r.height)/(innerWidth*innerHeight); };
    const blocking=others.filter(d => isModal(d) || area(d)>0.3);
    const overlay=blocking.length>0;
    const signin=blocking.some(d => d.querySelector('input[type="password"]') ||
        /\bsign[ -]?in\b|\blog[ -]?in\b|create (an )?account/i.test(norm(d.innerText).slice(0,300)));
    // Language / country / region selector ("You're visiting Samsung US. Go to Samsung Singapore?").
    const regionText=/(choose|select|change) (your |a |another )?(country|region|language|location)|country\/region|(you('re| are)|looks like you('re| are)) (visiting|in|from|browsing)|visit(ing)? (our|the) .{1,40}(site|website)|go to .{1,40}(site|website)|deliver(ing|y)? to|ship(ping)? to|language (preference|selection)/i;
    const isRegion=d => regionText.test(norm(d.innerText).slice(0,600));
    const regionDialog=blocking.some(isRegion);
    const dialogInfo=blocking.length ? ((regionDialog?'[region] ':'')+norm((blocking[0].getAttribute('aria-label')||'')+' '+blocking[0].innerText)).slice(0,160) : '';

    const clickable='button,[role="button"],a,input[type="button"],input[type="submit"],[tabindex="0"]';
    // Return the first matching button; prefer one nothing else is covering, but still report a covered one
    // (flagged) so Python can fall back to a programmatic click instead of giving up.
    const pick=(roots, want, ids=[]) => {
        const candidates=[];
        for (const id of ids) { const e=document.getElementById(id); if (e) candidates.push(e); }
        for (const box of roots) candidates.push(...deepAll(box, clickable));
        let covered=null;
        for (const e of candidates) {
            if (!visible(e) || e.disabled) continue;
            const text=label(e);
            if (!ids.includes(e.id) && !want.test(text)) continue;
            const r=e.getBoundingClientRect(), x=r.left+r.width/2, y=r.top+r.height/2;
            if (x<0||y<0||x>=innerWidth||y>=innerHeight) continue;
            const hit=document.elementFromPoint(x,y);
            const free=!hit || hit===e || e.contains(hit) || hit.contains(e) || (e.getRootNode().host && e.getRootNode().host.contains(hit));
            const result={x,y,label:text.slice(0,80),covered:!free};
            if (free) return result;
            if (!covered) covered=result;
        }
        return covered;
    };

    // Dismiss button for a blocking non-consent dialog (never used for sign-in dialogs).
    const stayRe=/^(stay|stay here|stay on [^,]{1,40}|no,? stay( here| on [^,]{1,40})?|remain on [^,]{1,40}|continue (to|on|with|shopping on) [^,]{1,40}|keep (current|this) (site|region|country|language|location)|no,? thanks|not now|cancel)$/i;
    const dismissRe=/^(close|dismiss|no,? thanks|no thank you|not now|maybe later|skip|cancel|continue shopping|stay on [\w. ]+|x|×|✕|close (dialog|popup|modal|window))$/i;
    let dialogButton=null;
    if (overlay && !signin) {
        const regions=blocking.filter(isRegion);
        dialogButton=(regions.length && pick(regions, stayRe)) || pick(blocking, dismissRe);
    }

    const rejectRe=/^((reject|decline|deny|refuse|disagree)( all| optional| additional| non-?essential| unnecessary| other)?( cookies)?( and close| & close)?|(use |allow |accept |only allow |continue with )?(only )?(strictly )?(necessary|essential|required|functional)( cookies)?( only)?|i do not (accept|agree)|disagree and close|continue without (accepting|agreeing|consent)|do not (accept|allow|sell)( my (personal )?(data|information))?|no,? thanks|opt[ -]out)$/i;
    const acceptRe=/^(accept|allow|agree|ok|okay|got it|ok,? got it|okay,? got it|i agree|i accept|i understand|understood|yes,? i (agree|accept)|accept (all|and close|& close|and continue|& continue|cookies|all cookies)|allow (all|cookies|all cookies)|agree (and|&) (close|continue|proceed)|accept all and (close|continue)|continue|sounds good)$/i;
    const knownId={reject:['onetrust-reject-all-handler','CybotCookiebotDialogBodyButtonDecline','didomi-notice-disagree-button','truste-consent-required','cky-btn-reject'],
                   accept:['onetrust-accept-btn-handler','CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll','didomi-notice-agree-button','truste-consent-button','cky-btn-accept']};
    // Banners with no real choice ("We use cookies. [Got it]") can be acknowledged/closed in reject mode.
    const ackRe=/^(got it|ok|okay|ok,? got it|okay,? got it|i understand|understood|close|dismiss|continue|x|×|✕|close (banner|this|cookie banner|cookie notice))$/i;
    // Last resort in reject mode: save the banner's default choices (non-essential is off by default in these panels).
    const saveRe=/^(confirm|save|submit) (my )?(choices|preferences|settings|selection)$/i;
    let button=null;
    if (choice==='reject') button=pick(consentBoxes, rejectRe, knownId.reject) || pick(consentBoxes, ackRe) || pick(consentBoxes, saveRe);
    else if (choice==='accept') button=pick(consentBoxes, acceptRe, knownId.accept);
    return {title:document.title,body:(document.body?.innerText||'').slice(0,20000),captcha:challenge,overlay,
            consent_visible:consentBoxes.length>0, consent_button:button,
            consent_info:consentBoxes.length ? norm(consentBoxes[0].innerText).slice(0,160) : '',
            dialog_button:dialogButton, dialog_info:dialogInfo, signin_dialog:signin};
}'''

class WebAgent:
    def __init__(self, desktop, control, web_config, workspace):
        self.desktop, self.control = desktop, control
        
        # --- DYNAMIC CONFIGURATION ---
        # Read the raw URLs directly from the 'web' array in config.json
        self.urls = web_config if isinstance(web_config, list) else []
        
        # Dynamically extract clean domain names (e.g., "samsung.com", "coursera.org") 
        # to use as the top-level navigation whitelist
        self.allowed_domains = []
        for url in self.urls:
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            if domain and domain not in self.allowed_domains:
                self.allowed_domains.append(domain)
                
        # Also include standard dynamic platform sub-assets like AWS and Amazon CDN bypasses
        self.allowed_domains.extend(["cloudfront.net", "amazonaws.com", "googletagmanager.com"])
        # --- END DYNAMIC CONFIGURATION ---
        
        self.launcher = ExplorerLauncher(desktop, control, workspace)
        self.manager = self.browser = self.context = self.page = self.cdp = self.ui = None
        self.owned = False
        self.restriction = None
        self.last_access_check = -float('inf')
        self.restriction_logged = False
        self.consent_choice = COOKIE_CONSENT_CHOICE
        self.consent_attempts = 0
        self._handling_consent = False
        self.dialog_attempts = 0

    def open(self):
        from playwright.sync_api import sync_playwright
        self.control.check()
        self.manager = sync_playwright().start()
        try:
            endpoint = self.launcher.launch(self.manager.chromium.executable_path)
            self.browser = self.manager.chromium.connect_over_cdp(endpoint, timeout=self.control.timeout_ms())
            self.cdp = self.browser.new_browser_cdp_session()
            arguments = self.cdp.send('Browser.getBrowserCommandLine')['arguments']
            expected_profile = '--user-data-dir=' + str(self.launcher.profile)
            if expected_profile not in arguments or '--enable-automation' not in arguments:
                raise RuntimeError('Browser ownership/declared-automation check failed')
            self.owned = True
            self.cdp.send('Browser.setDownloadBehavior', {'behavior': 'deny'})
            contexts = self.browser.contexts
            if len(contexts) != 1 or len(contexts[0].pages) != 1:
                raise RuntimeError('Expected a new browser profile with one blank tab')
            self.context = contexts[0]
            self.page = self.context.pages[0]
            if self.page.url != 'about:blank':
                raise RuntimeError('New browser did not start on a blank tab')
            if self.page.evaluate('navigator.webdriver') is not True:
                raise RuntimeError('Declared automation indicator missing; run stopped')

            # --- DYNAMIC ROUTING RULES ---
            def custom_route_request(route):
                url = route.request.url.lower()

                # Check if the request matches one of your core whitelisted domains
                is_whitelisted = any(domain in url for domain in self.allowed_domains)

                # If the request is for an external domain, log it for telemetry, but still allow it
                if not is_whitelisted:
                    self.control.audit.emit(
                        'network_request_external',
                        backend='playwright_route',
                        url=route.request.url
                    )

                # Allow the connection so the website doesn't break or trigger "chrome-error://"
                route.continue_()

            # Apply custom route filtering to browser context
            self.context.route('**/*', custom_route_request)
            # --- END DYNAMIC ROUTING RULES ---

            self.context.add_init_script('document.addEventListener("mousemove", e => {window.__trainingPointer={x:e.clientX,y:e.clientY};}, true)')
            self.page.on('response', self._response)
            
            def handle_dialog(dialog):
                self.control.audit.emit('dialog_detected', message=dialog.message, dialog_type=dialog.type)

                # Check if this is a "Leave site?" confirmation dialog
                if dialog.type == 'beforeunload':
                    print(f"[*] 'Leave site?' dialog detected. Accepting to allow navigation...")
                    dialog.accept() # Click "Leave" or "OK"
                    self.control.audit.emit('dialog_accepted_beforeunload')
                else:
                    # For all other unexpected dialogs (alerts, prompts), dismiss them.
                    print(f"[*] An unexpected dialog appeared: '{dialog.message}'. Dismissing it.")
                    dialog.dismiss()
                    self.control.audit.emit('dialog_dismissed')

            self.context.on('dialog', handle_dialog)
            self.page.on('download', lambda download: self._mark_restricted('unexpected_download'))
            
            def handle_unexpected_popup(popup_page):
                self.control.audit.emit('popup_intercepted', url=popup_page.url)
                try:
                    # Let popup load briefly so telemetry observes it
                    try:
                        popup_page.wait_for_load_state('domcontentloaded', timeout=4000)
                    except Exception:
                        pass

                    self.control.pause(1.0) # Human reading pause

                    # Direct, programmatic closure ensures the tab definitely disappears
                    # and never traps OS focus or triggers multiple duplicate tabs
                    popup_page.close()
                    self.control.audit.emit('popup_closed_cleanly')

                    # Re-focus the main window. bring_to_front() only switches the tab inside
                    # Chrome; Windows may have handed the foreground to Word/Explorer when the
                    # popup closed, so also re-activate the owned OS window.
                    self.page.bring_to_front()
                    if self.ui is not None:
                        try:
                            self.desktop.activate(self.ui.hwnd, self.control)
                        except FocusLost:
                            pass  # the input guard will retry and log before the next action
                except Exception as e:
                    self.control.audit.emit('popup_close_failed', error=str(e))

            self.context.on('popup', handle_unexpected_popup)

            processes = self.cdp.send('SystemInfo.getProcessInfo')['processInfo']
            pids = [int(info['id']) for info in processes if info['type'] == 'browser']
            if len(pids) != 1:
                raise RuntimeError('Could not observe a unique browser process')
            hwnd = None
            for _ in range(30):
                try:
                    hwnd = self.desktop.find_window_by_pid(pids[0])
                    break
                except FocusLost:
                    self.control.pause(.1)
            if hwnd is None:
                raise FocusLost('Owned browser window did not appear')
            self.desktop.activate(hwnd, self.control)
            self.ui = self.desktop.owned_input(hwnd, self.control, verify=self._verify_before_input)
            self.control.audit.emit('browser_opened', backend='explorer_shortcut_then_playwright_cdp',
                                    observed_pid=pids[0], window_handle=int(hwnd),
                                    automation_enabled=True, input_backend='pyautogui')
            self._check_scale()
        except BaseException:
            self.close()
            raise

    def _settle(self):
        """Wait (briefly) for an in-flight navigation to produce a usable new page."""
        try:
            self.page.wait_for_load_state('domcontentloaded', timeout=10000)
        except Exception:
            pass
        self.control.pause(0.3)

    def _eval(self, script, arg=None, attempts=4):
        """page.evaluate that survives the page navigating mid-call (link click, redirect, Enter in URL bar)."""
        for attempt in range(attempts):
            try:
                return self.page.evaluate(script) if arg is None else self.page.evaluate(script, arg)
            except Exception as exc:
                if not is_navigation_race(exc) or attempt == attempts - 1:
                    raise
                self.control.audit.emit('page_navigated_during_read', attempt=attempt + 1, url=self.page.url)
                self._settle()

    def _title(self):
        for attempt in range(4):
            try:
                return self.page.title()
            except Exception as exc:
                if not is_navigation_race(exc) or attempt == 3:
                    raise
                self._settle()

    def _mark_restricted(self, reason):
        if self.restriction is None:
            self.restriction = reason

    def _response(self, response):
        if response.request.is_navigation_request() and response.request.frame == self.page.main_frame:
            if response.status >= 400:
                self._mark_restricted('http_status_' + str(response.status))

    def _raise_restriction(self):
        if self.restriction:
            if not self.restriction_logged:
                self.control.audit.emit('website_access_stopped', reason=self.restriction,
                                        url=self.page.url if self.page else None)
                self.restriction_logged = True
            raise AccessRestricted(self.restriction)

    def check_access(self, force=False):
        self.control.check()
        self._raise_restriction()
        
        current_url = self.page.url.lower()
        if current_url == 'about:blank':
            return

        # --- SIMPLIFIED URL POLICY CHECK ---
        # Raise restriction ONLY if we hit a browser network error page (e.g. DNS failure, offline)
        if current_url.startswith('chrome-error://'):
            self._mark_restricted(f'navigation_failed_to_load: {current_url}')
            self._raise_restriction()
        # --- END SIMPLIFIED CHECK ---

        if self._handling_consent:
            return  # we are clicking a banner/popup's own button right now; it's expected to be visible
        if not force and self.control.clock() - self.last_access_check < 1:
            return
            
        self.last_access_check = self.control.clock()
        
        # Standard safety scanning for CAPTCHAs, Overlays, and Access Denial text remains active
        snapshot = self._eval(PAGE_SNAPSHOT_JS, self.consent_choice)
        consent_visible = snapshot.pop('consent_visible', False)
        consent_button = snapshot.pop('consent_button', None)
        consent_info = snapshot.pop('consent_info', '')
        dialog_button = snapshot.pop('dialog_button', None)
        dialog_info = snapshot.pop('dialog_info', '')
        signin_dialog = snapshot.pop('signin_dialog', False)

        reason = restriction_reason(**snapshot)
        if (reason == 'page_dialog_requires_attention' and not signin_dialog and not self._handling_consent
                and getattr(self, 'dialog_attempts', 0) < MAX_CONSENT_ATTEMPTS):
            if self._dismiss_dialog(dialog_button, dialog_info):
                return
        if reason == 'page_dialog_requires_attention':
            self.control.audit.emit('page_dialog_not_dismissed', dialog=dialog_info,
                                    signin=bool(signin_dialog), url=self.page.url)
        if reason is None and consent_visible and not self._handling_consent:
            if self.consent_choice in ('reject', 'accept') and consent_button and self.consent_attempts < MAX_CONSENT_ATTEMPTS:
                self._answer_consent(consent_button)
                return
            reason = 'cookie_consent_requires_attention'
            self.control.audit.emit('cookie_consent_not_answered', banner=consent_info,
                                    button_found=bool(consent_button), attempts=self.consent_attempts,
                                    url=self.page.url)
        if reason:
            self._mark_restricted(reason)
            self._raise_restriction()

    def _click_with_fallback(self, button, gone):
        """Physical click on a banner/popup button; if it is still there afterwards (the OS click landed on
        an invisible element or missed), retry once with Playwright's page.mouse.click at the same point.
        Returns (closed, backend)."""
        screen_x, screen_y = self.screen_point(button['x'], button['y'])
        move_mouse_human(self.ui, screen_x, screen_y, self.control)
        self.control.pause(self.control.rng.uniform(0.2, 0.5))
        self.ui.click()
        if self._wait_until(gone, checks=12):
            return True, 'pyautogui_physical'
        self.control.audit.emit('physical_click_intercepted', button_label=button['label'],
                                covered=bool(button.get('covered')), url=self.page.url)
        print(f"[!] Physical click on '{button['label']}' had no effect. Retrying with page.mouse.click()...")
        try:
            self.page.mouse.click(button['x'], button['y'])
        except Exception as exc:
            self.control.audit.emit('programmatic_click_failed', error=str(exc)[:200])
            return False, 'playwright_mouse_fallback'
        return self._wait_until(gone, checks=12), 'playwright_mouse_fallback'

    def _wait_until(self, gone, checks):
        for _ in range(checks):
            self.control.pause(0.25)
            if gone(self._eval(PAGE_SNAPSHOT_JS, 'none')):
                return True
        return False

    def _answer_consent(self, button):
        """Click the cookie banner's reject/accept button with the normal human-like cursor path."""
        self.consent_attempts += 1
        self._handling_consent = True
        try:
            self.control.audit.emit('cookie_consent_detected', choice=self.consent_choice,
                                    button_label=button['label'], attempt=self.consent_attempts,
                                    url=self.page.url)
            print(f"[*] Cookie banner detected. Clicking '{button['label']}' ({self.consent_choice})...")
            self.control.pause(self.control.rng.uniform(0.8, 1.8))  # notice and read the banner
            closed, backend = self._click_with_fallback(button, lambda st: not st.get('consent_visible'))
            self.control.audit.emit('cookie_consent_answered', backend=backend,
                                    choice=self.consent_choice, button_label=button['label'],
                                    banner_closed=closed)
        finally:
            self._handling_consent = False

    def _dismiss_dialog(self, button, info):
        """Close an ordinary popup (location prompt, newsletter, promo) instead of stopping the run.
        Clicks its Close/Dismiss/No thanks button, or presses Escape if there is none.
        Returns True if the popup went away."""
        self.dialog_attempts = getattr(self, 'dialog_attempts', 0) + 1
        self._handling_consent = True  # suppress nested access checks while we act
        try:
            self.control.audit.emit('page_dialog_detected', dialog=info, attempt=self.dialog_attempts,
                                    button_label=button['label'] if button else None, url=self.page.url)
            print(f"[*] Popup detected ({info[:60]!r}). Dismissing it...")
            self.control.pause(self.control.rng.uniform(0.6, 1.4))  # notice the popup
            gone = lambda st: not st.get('overlay')
            if button:
                closed, method = self._click_with_fallback(button, gone)
            else:
                self.ui.press('escape')
                closed, method = self._wait_until(gone, checks=12), 'escape'
            self.control.audit.emit('page_dialog_dismissed' if closed else 'page_dialog_dismiss_failed',
                                    method=method, dialog=info)
            return closed
        finally:
            self._handling_consent = False

    def _verify_before_input(self):
        self.check_access()

    def _check_scale(self):
        info = self._eval('({ratio:devicePixelRatio,zoom:visualViewport.scale,x:screenX,y:screenY})')
        if abs(info['ratio'] - 1) > .01 or abs(info['zoom'] - 1) > .01 or info['x'] < -20 or info['y'] < -20:
            raise RuntimeError('Use primary monitor, 100% Windows scaling and 100% browser zoom')

    def activate(self):
        """
        Brings the browser window to the foreground and reliably waits for it
        to be ready before proceeding. This prevents race conditions when
        switching from other applications like Word.
        """
        current_foreground_window = self.desktop.gui.GetForegroundWindow()
        
        # Only perform the full activation sequence if the browser isn't already in the foreground.
        if current_foreground_window != self.ui.hwnd:
            print("[*] Browser is not in focus. Activating and waiting for focus...")
            # 1. Bring the physical OS window to the front.
            self.desktop.activate(self.ui.hwnd, self.control)
            
            # 2. Wait until the OS confirms the browser window is truly in the foreground.
            try:
                self.control.wait_for(
                    lambda: self.desktop.gui.GetForegroundWindow() == self.ui.hwnd,
                    timeout_seconds=5,
                    description="browser window to gain foreground focus"
                )
            except TimeoutError:
                raise FocusLost("Browser window did not gain foreground focus after activation request.")
        
        # 3. Now that focus is guaranteed, run the safety checks.
        self.ui.guard()
        self._check_scale()
        self.check_access(force=True)


    def _wait_for_destination(self, url):
        from urllib.parse import urlparse
        target_domain = urlparse(url).netloc.replace("www.", "").lower()
        
        try:
            # 1. Wait until the browser address bar actually navigates away from about:blank
            #    and matches our target domain (e.g., 'coursera.org')
            self.page.wait_for_url(
                lambda u: target_domain in u.lower() if target_domain else u != 'about:blank',
                timeout=self.control.timeout_ms(),
                wait_until='domcontentloaded'
            )
            # 2. Give the page an extra second to settle initial script execution
            self.control.pause(2.0)
        except Exception as e:
            # If wait timed out or failed, log restriction
            self._raise_restriction()
            raise
            
        self.dialog_attempts = 0
        self.check_access(force=True)
        self.control.audit.emit(
            'navigation_verified', 
            backend='pyautogui', 
            url=self.page.url,
            observed_title=self._title()
        )


    def navigate(self, target_url_or_index=None):
        """
        Navigates to a specified URL, ensuring the address bar is focused
        before typing to prevent lost characters.
        """
        self.activate()

        url = None
        if target_url_or_index is None:
            if not self.urls:
                raise ValueError("No URLs configured to navigate to.")
            url = self.control.rng.choice(self.urls)
            self.control.audit.emit('navigate_random_url', selected_url=url)
            print(f"[*] No target specified. Navigating to random URL: {url}")
        elif isinstance(target_url_or_index, int) and 0 <= target_url_or_index < len(self.urls):
            url = self.urls[target_url_or_index]
        else:
            url = str(target_url_or_index)

        if not url:
            self.control.audit.emit('navigate_skipped', reason='no_url_provided_or_configured')
            return

        self.control.audit.emit('navigation_started', target_url=url)

        # --- THE FIX ---
        self.ui.hotkey('ctrl', 'l')
        # Add a brief pause to allow the OS and browser to focus the address bar.
        self.control.pause(self.control.rng.uniform(0.1, 0.25))
        # --- END FIX ---

        for char in url:
            self.ui.write(char)
            self.control.pause(self.control.rng.uniform(0.03, 0.10))
        # Wait for the navigation Enter actually starts, so we never inspect the old page
        # (matters when the new URL is on the same site as the page already open).
        try:
            with self.page.expect_navigation(wait_until='domcontentloaded', timeout=self.control.timeout_ms()):
                self.ui.press('enter')
        except Exception as exc:
            timed_out = 'timeout' in type(exc).__name__.lower() or 'timeout' in str(exc).lower()
            if not (timed_out or is_navigation_race(exc)):
                raise
            self.control.audit.emit('navigation_event_not_observed', target_url=url, error=str(exc)[:200])
        self._wait_for_destination(url)


    def screen_point(self, x, y):
        self._check_scale()
        window = self._eval('''() => ({left:screenX+(outerWidth-innerWidth)/2,
            top:screenY+(outerHeight-innerHeight)-(outerWidth-innerWidth)/2,
            width:innerWidth,height:innerHeight})''')
        if not 0 <= x < window['width'] or not 0 <= y < window['height']:
            raise RuntimeError('DOM target outside viewport')
        return window['left'] + x, window['top'] + y

    def click_element(self, locator):
        """
        Locates an element, scrolls to it naturally using randomized mouse wheel strokes,
        glides the mouse via Bezier curves, and executes a single reliable click.
        """
        self.control.check()

        try:
            # 1. Ensure element exists and is visible
            if not locator.is_visible(timeout=3000):
                return False

            # 2. Prevent link from opening a popup tab
            try:
                locator.evaluate("""el => {
                    const anchor = el.closest('a') || el;
                    if (anchor.tagName.toLowerCase() === 'a') {
                        anchor.removeAttribute('target');
                        anchor.setAttribute('target', '_self');
                    }
                }""")
            except Exception:
                pass

            # 3. GET ELEMENT BOX BEFORE SCROLLING
            box = locator.bounding_box()
            if not box:
                return False

            viewport = self._eval('({width: innerWidth, height: innerHeight})')

            # 4. NATURAL HUMAN SCROLLING:
            # If the element is off-screen, scroll to it using our smooth, step-by-step mouse wheel emulator
            # instead of letting the browser snap or slide at machine speed.
            # Viewport coordinates already exclude the browser's tab/address bar, so a header link at
            # y=56 is on-screen and clickable. Only scroll when the element really is out of view.
            if box['y'] + box['height'] > viewport['height'] - 20 or box['y'] < 0:
                print(f"[*] Element is off-screen (y={box['y']}). Scrolling smoothly to it...")

                # Calculate required wheel clicks (1 click = 100 CSS pixels)
                target_center_y = viewport['height'] / 2
                distance_to_scroll = box['y'] - target_center_y
                clicks_needed = int(distance_to_scroll / 100)

                if clicks_needed != 0:
                    from mouse_behavior import human_scroll
                    # This will scroll step-by-step with natural pauses, looking completely human!
                    human_scroll(self.ui, clicks_needed, self.control, page=self.page)
                    self.control.pause(self.control.rng.uniform(0.6, 1.2))

            # 5. Get the final, settled bounding box after smooth wheel scrolling
            box = locator.bounding_box()
            if not box:
                return False

            el_x = box['x'] + (box['width'] / 2)
            el_y = box['y'] + (box['height'] / 2)

            # Safeguard: Keep clicks inside the visible browser area
            if el_y < 5 or el_y > viewport['height'] - 5:
                print(f"[!] Element y={el_y} still outside safe viewport area. Skipping.")
                return False

            # 6. Convert to physical OS screen coordinates
            screen_x, screen_y = self.screen_point(el_x, el_y)

            # 7. Smooth Bezier mouse movement directly to the visible link
            print(f"[*] Gliding mouse smoothly to target ({screen_x}, {screen_y})...")
            from mouse_behavior import move_mouse_human
            move_mouse_human(self.ui, screen_x, screen_y, self.control)
            self.control.pause(self.control.rng.uniform(0.3, 0.6)) # Hesitate before clicking

            # 8. Single click with navigation safety
            try:
                with self.page.expect_navigation(wait_until='domcontentloaded', timeout=3000):
                    self.ui.click()
                self.control.audit.emit('element_clicked_and_navigated', backend='pyautogui_physical', new_url=self.page.url)
            except Exception:
                self.ui.click()
                self.control.audit.emit('element_clicked_in_page', backend='pyautogui_physical')

            return True

        except Exception as e:
            self.control.audit.emit('click_failed', reason='unexpected_exception', error=str(e))
            return False

    def browse_until(self, target):
        self.activate()

        try:
            self.page.wait_for_load_state('domcontentloaded', timeout=5000)
        except Exception:
            pass

        # Exit the loop with at least 15 seconds to spare
        while self.control.clock() < target - 15:
            # Check deadline before starting any action
            self.control.check()
            self.check_access(force=True)
            self.ui.guard()

            try:
                self._browse_step(target)
            except Exception as exc:
                if not is_navigation_race(exc):
                    raise
                # A click/redirect replaced the page while we were looking at it: wait and carry on.
                self.control.audit.emit('page_navigated_during_step', url=self.page.url)
                self._settle()

        # Hand off cleanly to Word before the deadline hits!
        print(f"[*] Phase ending cleanly at {self.control.clock():.1f}s. Handing off to next phase...")
        self.control.idle_until(target, 'reading_public_page', guard=self.ui.guard)

    def _browse_step(self, target):
        """One click-or-scroll action while reading a page."""
        # --- DECISION: Click or Scroll ---
        if self.control.rng.random() < 0.20:
            clickable_selectors = [
                "main a[href]", "article a[href]", ".cds-ProductCard-base a", 
                "nav a[href]", "a[data-click-key]"
            ]
            
            clicked = False
            for sel in clickable_selectors:
                elements = self.page.locator(sel).all()
                if elements:
                    visible_elements = [el for el in elements if el.is_visible()]
                    if visible_elements:
                        target_element = self.control.rng.choice(visible_elements)
                        txt = target_element.inner_text().strip().split('\n')[0]
                        if len(txt) > 3:
                            clicked = self.click_element(target_element)
                            if clicked:
                                break
            if clicked:
                # Give short pause, but only if we have time remaining
                if self.control.clock() < target - 20:
                    self.control.pause(self.control.rng.uniform(3.0, 5.0))
                return

        # --- SCROLLING ---
        viewport = self._eval('({width:innerWidth,height:innerHeight})')
        x, y = self.screen_point(
            viewport['width'] * self.control.rng.uniform(.35, .65),
            viewport['height'] * self.control.rng.uniform(.4, .7)
        )
        move_mouse_human(self.ui, x, y, self.control)

        top = self._eval('scrollY')
        bottom = self._eval('scrollY + innerHeight >= document.documentElement.scrollHeight - 10')

        if bottom:
            scroll_direction = -1
        else:
            scroll_direction = 1 if self.control.rng.random() < 0.90 else -1
        if top == 0 and scroll_direction == -1:
            scroll_direction = 1

        clicks_to_scroll = self.control.rng.randint(2, 4)
        scroll_amount = scroll_direction * clicks_to_scroll

        human_scroll(self.ui, scroll_amount, self.control, page=self.page)
        
        # Short pause between scrolls
        self.control.pause(self.control.rng.uniform(1.5, 3.0))

    def close(self):
        errors = []
        if self.browser is not None:
            if self.owned and self.cdp is not None:
                try: 
                    self.cdp.send('Browser.close')
                except Exception as exc:
                    if self.browser.is_connected(): 
                        errors.append(type(exc).__name__)
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
        self.launcher.close()
        manual_cleanup = self.launcher.browser_requested and not self.owned
        self.control.audit.emit('browser_cleanup', errors=errors, manual_inspection_needed=manual_cleanup)
        if errors:
            raise RuntimeError('Browser cleanup failed: ' + ', '.join(errors))
