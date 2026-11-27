#!/usr/bin/env python3
"""Run one command with {run} replaced by this run's folder name.

usage: run_id.py RUN_DIR -- COMMAND [ARG...]

Demonstration 2 opens a new incident on every run. The incident owner ledger refuses an id it already
holds (record-exists), so the id carries the run stamp: INC-DEMO2-{run} becomes INC-DEMO2-20261127T030000Z.
"""
import os
import sys


def main(argv):
    if len(argv) < 3 or argv[1] != "--":
        print(__doc__)
        return 2
    run = os.path.basename(os.path.normpath(argv[0]))
    cmd = [a.replace("{run}", run) for a in argv[2:]]
    os.execv(cmd[0], cmd)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
