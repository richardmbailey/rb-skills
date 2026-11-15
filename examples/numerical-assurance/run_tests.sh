#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "${RB_TEST_PYTHON:-python3}" "$root/tools/run_suite.py" "$@"
