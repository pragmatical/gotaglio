@echo off
pip install poetry
python -m venv .venv
.venv\Scripts\Activate
poetry install
