#!/usr/bin/python3

from threading import Thread
from wsgiref.simple_server import make_server, WSGIRequestHandler

class _QuietWSGIRequestHandler(WSGIRequestHandler):
    """WSGIRequestHandler logs to stderr. Override for a quiet version."""
    def log_message(self, fmt, *args):
        pass


class WebServerThread(Thread):
    """Tiny web server that runs in its own thread"""
    def __init__(self, port, app_function, noisy):
        Thread.__init__(self)
        self.daemon = True
        self.name = "WebServer"
        self.port = port
        self.app_function = app_function
        self.handler = WSGIRequestHandler if noisy else _QuietWSGIRequestHandler

    def run(self):
        httpd = make_server('', self.port, self.app_function, handler_class=self.handler)
        httpd.serve_forever()
