#!/usr/bin/python3

import os
import syslog

def _linux_ssh_cmd(host, config, remotecmd):
    """Execute a remote command on a linux host."""
    if os.system("/bin/ping -c 1 -W 1 " + host + "> /dev/null 2>&1") != 0:
        syslog.syslog(host + " appears to be down. Skipping.")
        return

    idclause = "" if config.keyfile == "" else "-i " + config.keyfile
    rlogin = config.remoteid + "@" + host
    command = "/usr/bin/ssh " + idclause + " " + rlogin + " " +remotecmd
    os.system(command)


def shutdown_linux_host(host, config):
    """Shutdown a remote Linux host."""
    _linux_ssh_cmd(host, config, "sudo /sbin/shutdown -h now")
