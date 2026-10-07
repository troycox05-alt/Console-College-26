#!/bin/sh
# Console College in its own window (macOS / Linux). Double-click or run ./play.command
cd "$(dirname "$0")"
exec python3 play.py "$@"
