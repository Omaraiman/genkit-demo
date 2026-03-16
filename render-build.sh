#!/usr/bin/env bash
# exit on error
set -o errexit

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# Synchronize dependencies based on uv.lock
# --frozen ensures that uv doesn't touch the lockfile and installs exactly what's there
uv sync --frozen
