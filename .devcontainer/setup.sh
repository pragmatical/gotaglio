#!/bin/bash

# Install Poetry
pip install poetry

# Create a virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    python -m venv .venv
fi

# Activate the virtual environment
. .venv/bin/activate

# Install project dependencies
poetry install

# Make gotag.sh executable
chmod +x gotag

# Add the workspace directory to the PATH
echo 'export PATH=$PATH:/workspaces/gotaglio' >> ~/.bashrc
echo '. .venv/bin/activate' >> ~/.bashrc
