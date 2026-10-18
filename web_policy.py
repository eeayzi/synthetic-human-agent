"""Public-page allowlist and conservative stop conditions. No bypass logic."""
from urllib.parse import urlsplit


class AccessRestricted(RuntimeError):
    pass


def canonical_url(url):
    if not isinstance(url,str) or any(ord(c)<33 or ord(c)==127 for c in url):
        raise ValueError('URL must not contain whitespace or control characters')
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname not in ('www.coursera.org', 'coursera.org')
            or parsed.username or parsed.password or parsed.port not in (None,443)):
        raise ValueError('Public browsing URLs must be HTTPS Coursera URLs without credentials')
    path = parsed.path.rstrip('/') or '/'
    if not (path.startswith('/browse/') or path.startswith('/learn/')):
        raise ValueError('Only public browse/course paths are allowed')
    return ('www.coursera.org',path)


def allowed_url(url, configured):
    try:
        return canonical_url(url) in {canonical_url(value) for value in configured}
    except (ValueError, TypeError):
        return False


def restriction_reason(title, body, captcha=False, overlay=False):
    if captcha:
        return 'visible_captcha_or_challenge'
    phrases = ('access denied', 'verify you are human', 'verify that you are human',
               'checking your browser', 'unusual traffic', 'automated requests',
               'too many requests', 'temporarily blocked', 'request blocked',
               'confirm you are not a robot', 'security verification required',
               'page not found', 'not available in your region', 'not available in your country')
    combined = (title+'\n'+body).casefold()
    if any(phrase in combined for phrase in phrases):
        return 'access_verification_or_restriction'
    if overlay:
        return 'page_dialog_requires_attention'
    return None
