"""Two preselected local pages; no Internet dependency or external accounts."""
from contextlib import contextmanager
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading


def pages(scenario, marker):
    result = {}
    for name, other, text in [('brief', 'reference', scenario['brief']),
                              ('reference', 'brief', scenario['reference'])]:
        paragraphs = ''.join('<p>'+html.escape(text)+'</p>' for _ in range(8))
        result['/'+name] = ('<!doctype html><meta charset="utf-8">'
            f'<title>{html.escape(marker)} - {name}</title>'
            '<style>body{font:22px system-ui;max-width:850px;margin:100px auto;line-height:1.8}'
            'nav{position:fixed;top:0;left:0;right:0;background:#e7efff;padding:14px;text-align:center}'
            'p{margin:70px 0}</style>'
            f'<nav><a id="next" href="/{other}">Open {other}</a></nav>'
            f'<h1>{html.escape(scenario["title"])}: {name}</h1>'
            '<p>Fictional data for an explicitly synthetic desktop demonstration.</p>'
            f'<main>{paragraphs}</main>').encode('utf-8')
    return result


@contextmanager
def serve_pages(content):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = content.get(self.path)
            if body is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    thread.join(timeout=0.01)
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
