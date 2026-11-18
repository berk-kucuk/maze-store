#!/usr/bin/env python3
"""Maze Store — browse and install packages from the Maze Linux repository."""
import sys

if __name__ == "__main__":
    if "--check-updates" in sys.argv[1:]:
        # The background check must not pull in Qt: see mazestore/core/checker.py.
        from mazestore.core.checker import run as check
        sys.exit(check())
    if "--pending-upgrades" in sys.argv[1:]:
        from mazestore.core.syscheck import run as pending
        sys.exit(pending())
    from mazestore.gui.app import run
    sys.exit(run())
