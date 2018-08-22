#!/usr/bin/python3

import time
import argparse
from types import SimpleNamespace
from threading import Thread
from wsgiref.simple_server import make_server, WSGIRequestHandler
from pathlib import Path
import configparser
import syslog
import daemon
from gpiozero import Button

import hostactions

event_time = time.time()
on_mains = True
event_stack = []
maxevents = 50

def loadconfig(filename):
    """Load configuration from file and return it as a namespace"""
    global maxevents
    cp = configparser.ConfigParser()
    cp.read(filename)

    config = SimpleNamespace()
    config.pollinterval = cp.getint('master', 'pollinterval', fallback=5)
    config.sensorpin = cp.getint('master', 'sensorpin', fallback=3)
    config.remoteid = cp.get('master', 'remote-id', fallback="pomona")
    config.keyfile = cp.get('master', 'key-file', fallback='')
    config.webserver_port = cp.get('master', 'webserver-port', fallback=8000)
    maxevents = cp.getint('master', 'events', fallback=50)
    #config.logfile = cp.get('master', 'log-file', fallback='/tmp/pomona.log')

    groups = []
    for name in filter(lambda x: x.startswith("group-"), cp.sections()):
        group = SimpleNamespace()
        group.name = name
        group.threshold = cp.getint(name, 'threshold', fallback=300)
        group.hosts = cp.get(name, 'hosts').split()
        group.action = cp.get(name, 'action', fallback="unknown_action")
        group.notified = False
        groups.append(group)
    config.groups = groups
    return config


def add_event(timestamp, desc):
    global event_stack, maxevents
    event = desc, timestamp
    event_stack.append(event)
    if len(event_stack) > maxevents:
        event_stack.pop(event_stack[0])


def triggered(sensor):
    """Event callback when the sensor detects power failure."""
    global event_time, on_mains
    event_time = time.time()
    on_mains = False
    add_event(event_time, 'TRIPPED')
    syslog.syslog("Power tripped at " + str(event_time))


def restored(sensor):
    """Event callback when the sensor detects power restored."""
    global event_time, on_mains
    event_time = time.time()
    on_mains = True
    add_event(event_time, 'RESTORED')
    syslog.syslog("Power restored at " + str(event_time))


def unknown_action(host, config):
    """Dummy action handler for missing/invalid action lines in .ini file"""
    syslog.syslog(syslog.LOG_ERR, "Unknown action for " + host)


def monitor_loop(config):
    """Main event loop for POMONA"""
    global event_time, on_mains, event_stack, maxevents

    if config.args.webserver:
        req_handler = QuietWSGIRequestHandler
        if config.args.verbose and config.args.foreground:
            req_handler = WSGIRequestHandler
        server = WebServerThread(config.webserver_port, webserver_app, req_handler)
        server.start()

    last_event_time = event_time = now = time.time()
    syslog.syslog("Started at " + str(now))
    add_event(event_time, 'STARTED')

    power_sensor = Button(config.sensorpin)
    on_mains = power_sensor.is_pressed

    power_sensor.when_released = triggered
    power_sensor.when_pressed = restored

    if not on_mains:
        syslog.syslog("Power loss!")
        add_event(event_time, 'TRIPPED')

    while True:
        now = time.time()
        elapsed = now - event_time

        if last_event_time != event_time:
            syslog.syslog("Resetting notification flags")
            for group in config.groups:
                group.notified = False
            last_event_time = event_time

        if not on_mains:
            for group in config.groups:
                if elapsed > group.threshold and not group.notified:
                    syslog.syslog("Triggering group: " +  group.name)
                    for host in group.hosts:
                        syslog.syslog("Notifying host " + host)
                        getattr(hostactions, group.action, unknown_action)(host, config)
                        add_event(now, "Notified " + host)
                    group.notified = True

        else:
            # TODO: do restart work here if set in config
            pass

        if config.args.verbose and config.args.foreground:
            print("on_mains = "+str(on_mains)+" for "+str(elapsed)+" seconds")
        time.sleep(config.pollinterval)


def webserver_app(environ, start_response):
    global event_stack, on_mains

    status = '200 OK'
    headers = [('Content-type', 'text/plain; charset=utf-8')]

    start_response(status, headers)
    ret = []
    state = "On Mains" if on_mains else "Power Tripped"
    ret.append(("Current State: " + state + "\n").encode("utf-8"))
    ret.append("Events:\n".encode("utf-8"))

    ret.extend([("%s: %s\n" % (time.strftime("%Y-%m-%d %T", time.localtime(val[1])), val[0])).encode("utf-8") for val in event_stack])
    return ret

class QuietWSGIRequestHandler(WSGIRequestHandler):
    def log_message(self, fmt, *args):
        pass

class WebServerThread(Thread):
    def __init__(self, port, app_function, req_handler):
        Thread.__init__(self)
        self.port = port
        self.app_function = app_function
        self.req_handler = req_handler

    def run(self):
        httpd = make_server('', self.port, self.app_function, handler_class=self.req_handler)
        httpd.serve_forever()


def do_main():
    """Main function"""
    syslog.openlog("Pomona", facility=syslog.LOG_DAEMON)

    try:
        parser = argparse.ArgumentParser(
                description="Pomona - Power Monitor Appliance")
        parser.add_argument('-c', '--config', default='/etc/pomona/pomona.ini',
                help='config file (default: /etc/pomona/pomona.ini)')
        parser.add_argument('-v', '--verbose', action='store_true',
                help='be more noisy')
        parser.add_argument('-F', '--foreground', action='store_true',
                help="run in foreground and don't beome a daemon")
        parser.add_argument('-w', '--webserver', action='store_true',
                help="run webserver showing event history. Default port: 8000")
        args = parser.parse_args()

        cfg_file = Path(args.config)
        if not cfg_file.is_file():
            print("Error: Cannot read configuration from ", args.config)
            parser.print_help()
            return

        config = loadconfig(args.config)
        config.args = args

        if args.foreground:
            monitor_loop(config)
        else:
            syslog.syslog("Running as a daemon")
            with daemon.DaemonContext():
                monitor_loop(config)

    except Exception as exc:
        syslog.syslog(syslog.LOG_ERR, "Caught an exception")
        syslog.syslog(syslog.LOG_ERR, str(exc))


if __name__ == "__main__":
    do_main()
