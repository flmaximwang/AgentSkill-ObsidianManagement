#!/bin/sh
# organize.sh - one-line launcher for organize_notes.py
#
#   ./organize.sh "<target>"              dry run, prints the plan summary
#   ./organize.sh "<target>" apply        apply the plan (collisions skipped)
#   ./organize.sh --rollback plan.json    undo one applied plan
#   ./organize.sh "<target>" --max-level 12 --limit 26      extra flags pass through
#
# Picks the first working interpreter (Chinese pinyin needs none: macOS uses the
# system ICU, Linux/Windows optionally use pypinyin if installed).
set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROG="$HERE/organize_notes.py"

pick_python() {
    for c in "${PYTHON:-}" python3.12 python3.11 python3.10 python3 py; do
        [ -n "$c" ] || continue
        if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info>=(3,9) else 1)' 2>/dev/null; then
            printf '%s' "$c"; return 0
        fi
    done
    echo "no Python >= 3.9 found; set PYTHON=/path/to/python3" >&2
    return 1
}
PY=$(pick_python)

if [ "$#" -eq 0 ]; then
    sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
    exit 2
fi

case "$1" in
    --rollback|-h|--help|--selftest)
        exec "$PY" "$PROG" "$@"
        ;;
esac

TARGET=$1; shift
case "${1:-}" in
    apply)
        shift
        echo "== dry run first (nothing is written) =="
        "$PY" "$PROG" "$TARGET" "$@"
        echo "== applying =="
        exec "$PY" "$PROG" "$TARGET" --apply --on-collision skip "$@"
        ;;
    *)
        exec "$PY" "$PROG" "$TARGET" "$@"
        ;;
esac
