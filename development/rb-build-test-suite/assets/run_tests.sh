#!/bin/sh
# Bootstrap only: the executable runner is supplied and qualified separately.
set -eu
project_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
runner="$project_dir/.rb-tests/runner/run_checks.py"
if [ ! -f "$runner" ]; then
    printf '%s\n' 'Saved test runner is absent; completion is incomplete.' >&2
    exit 3
fi
exec "${RB_TEST_SUITE_PYTHON:-python3}" "$runner" --project-root "$project_dir" "$@"
