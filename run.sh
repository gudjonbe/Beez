#!/usr/bin/env bash
set -euo pipefail
python -m uvicorn bee_sim.main:app --reload --port 8000
