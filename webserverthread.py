#!/usr/bin/python3

from threading import Thread
from wsgiref.simple_server import make_server, WSGIRequestHandler

class _QuietWSGIRequestHandler(WSGIRequestHandler):
    def log_message(self, fmt, *args):
        pass

class WebServerThread(Thread):
    def __init__(self, port, app_function, quiet):
        Thread.__init__(self)
        self.port = port
        self.app_function = app_function
        self.handler = _QuietWSGIRequestHandler if quiet else WSGIRequestHandler

    def run(self):
        httpd = make_server('', self.port, self.app_function, handler_class=self.handler)
        httpd.serve_forever()
