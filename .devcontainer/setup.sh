#!/bin/bash

# Install Poetry
pip install poetry

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install project dependencies
poetry install

# Make gotag.sh executable
chmod +x gotag

# Add the workspace directory to the PATH
echo 'export PATH=$PATH:/workspace' >> ~/.bashrc
