#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [[ -x .venv/bin/python ]]; then
  exec .venv/bin/python app.py
elif [[ -x ../../.venv/bin/python ]]; then
  exec ../../.venv/bin/python app.py
else
  printf '%s\n' 'Create the environment first; see README.md.' >&2
  exit 1
fi
