"""
WSGI adapter for the CLTIBC website — lets hosts like PythonAnywhere run
server.py without any changes to the application itself.

Point the host's WSGI config at `application` in this file.
"""
import io
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import server  # noqa: E402  (loads config, routes, everything)


class _OneShotHandler(server.Handler):
    """Runs a single already-parsed request and captures the raw response."""

    def __init__(self, raw_request, client_ip):  # no socket, no server
        self.rfile = io.BytesIO(raw_request)
        self.wfile = io.BytesIO()
        self.client_address = (client_ip, 0)
        self.requestline = ""
        self.request_version = "HTTP/1.1"
        self.command = ""
        self.close_connection = True
        self.raw_requestline = self.rfile.readline()
        if not self.parse_request():
            return
        method = getattr(self, "do_" + self.command, None)
        if method is None:
            self.send_error(501)
            return
        method()

    def log_message(self, fmt, *args):
        pass


def application(environ, start_response):
    method = environ["REQUEST_METHOD"]
    path = environ.get("PATH_INFO", "/") or "/"
    query = environ.get("QUERY_STRING", "")
    if query:
        path += "?" + query

    length = int(environ.get("CONTENT_LENGTH") or 0)
    body = environ["wsgi.input"].read(length) if length else b""

    lines = ["%s %s HTTP/1.1" % (method, path)]
    if environ.get("CONTENT_TYPE"):
        lines.append("Content-Type: %s" % environ["CONTENT_TYPE"])
    if length:
        lines.append("Content-Length: %d" % length)
    for key, value in environ.items():
        if key.startswith("HTTP_") and key not in ("HTTP_CONTENT_TYPE", "HTTP_CONTENT_LENGTH"):
            lines.append("%s: %s" % (key[5:].replace("_", "-").title(), value))
    raw = ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + body

    handler = _OneShotHandler(raw, environ.get("REMOTE_ADDR", "0.0.0.0"))
    response = handler.wfile.getvalue()

    head, _, payload = response.partition(b"\r\n\r\n")
    head_lines = head.decode("latin-1").split("\r\n")
    status = head_lines[0].split(" ", 1)[1] if " " in head_lines[0] else "500 Error"
    headers = []
    for line in head_lines[1:]:
        if ": " in line:
            name, value = line.split(": ", 1)
            if name.lower() not in ("connection", "server", "date"):
                headers.append((name, value))

    start_response(status, headers)
    return [payload]
