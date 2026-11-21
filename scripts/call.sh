#!/usr/bin/env bash
# One DelegateCourt method call: build -> sign -> broadcast.
# Usage: ./call.sh <ROLE> <CONTRACT> <FUNCTION> '<jsonArgs>' [tag]
# ROLE: delegator | delegate. Prints the tx hash and saves the result JSON to
# /tmp/dl_<tag>.json (default /tmp/dl_call.json).
set -euo pipefail
cd "$(dirname "$0")"
ROLE="$1"; CONTRACT="$2"; FN="$3"; ARGS="$4"; TAG="${5:-call}"
SENDER=$(../.venv/bin/python -c "import json,sys; print(json.load(open('../.keys/keypairs.json'))['$ROLE']['address'])")
SENDER="$SENDER" node build_call.mjs "$CONTRACT" "$FN" "$ARGS" > "/tmp/dl_build_$TAG.log" 2>&1
awk '/---TX---/{flag=1;next}flag' "/tmp/dl_build_$TAG.log" > "/tmp/dl_tx_$TAG.json"
../.venv/bin/python sign_broadcast.py "$ROLE" "/tmp/dl_tx_$TAG.json" "/tmp/dl_$TAG.json"
