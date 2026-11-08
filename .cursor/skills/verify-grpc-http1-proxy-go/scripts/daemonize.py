#!/usr/bin/env python3
"""Start a command in its own session and record the daemon pid.

The parent returns only after the grandchild pid is on disk. The daemon is not
in the caller's process group, so the verification processes keep running after
control-proxy launch exits.

Usage: daemonize.py LOGFILE PIDFILE COMMAND [ARGS...]
"""

import os
import sys


def main() -> int:
    if len(sys.argv) < 4:
        sys.stderr.write("usage: daemonize.py LOGFILE PIDFILE COMMAND [ARGS...]\n")
        return 2
    logfile, pidfile = sys.argv[1], sys.argv[2]
    argv = sys.argv[3:]
    read_fd, write_fd = os.pipe()
    first = os.fork()
    if first > 0:
        os.close(write_fd)
        with os.fdopen(read_fd) as pipe:
            text = pipe.read().strip()
        if not text:
            sys.stderr.write("daemonize: child did not report a pid\n")
            return 1
        with open(pidfile, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
        os.waitpid(first, 0)
        return 0

    os.close(read_fd)
    os.setsid()
    second = os.fork()
    if second > 0:
        os.write(write_fd, f"{second}\n".encode())
        os.close(write_fd)
        os._exit(0)

    os.close(write_fd)
    log_fd = os.open(logfile, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.dup2(log_fd, 1)
    os.dup2(log_fd, 2)
    if log_fd > 2:
        os.close(log_fd)
    null_fd = os.open("/dev/null", os.O_RDONLY)
    os.dup2(null_fd, 0)
    if null_fd > 2:
        os.close(null_fd)
    os.execv(argv[0], argv)
    return 127


if __name__ == "__main__":
    sys.exit(main())
