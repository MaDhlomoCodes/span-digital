#!/usr/bin/env bash
# Usage: scripts/standings.sh "1974-75 First Division — Weeks 1-10 (complete).csv" [--max-week N]
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <matches.csv> [--max-week N]" >&2
    exit 1
fi

INPUT="$(realpath "$1")"
shift
OUTPUT="$PWD/output.csv"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$ROOT"
python -m src.main "$INPUT" "$@" > "$OUTPUT"
echo "Wrote $OUTPUT"