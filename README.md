# GoTaglio

Gotaglio is a lightweight python toolbox for creating ML pipelines for model evaluation and case labelling.

## Building GoTaglio

1. Verify you have python version >=3.12. Note that 3.13 may not be supported yet.
1. `pip install poetry` outside of any virtual environment
1. `git clone gotaglio`
1. `cd gotaglio`
1. `python -m venv .venv`
1. `.venv\Scripts\activate`
1. `poetry install`

## Running GoTaglio

~~~sh
% gotag
usage: gotag [-h] {help,history,models,pipelines,rerun,run,summarize,compare} ...

A tool for managing and running ML pipelines.

positional arguments:
  {help,history,models,pipelines,rerun,run,summarize,compare}
                        Subcommands
    help                Show help for gotag
    history             Show information about recent runs
    models              List available models
    pipelines           List available pipelines
    rerun               Rerun an experiment with modifications.
    run                 Run a named pipeline
    summarize           Summarize a run
    compare             Compare two or more label sets

options:
  -h, --help            show this help message and exit
~~~

~~~sh
python apps/example.py run data/cases.json simple template=data/template.txt model=gpt3.5
python apps\example.py run data\cases.json simple2 template=data\template.txt model=gpt3.5
python apps\example.py run data\small.json simple prepare.template=data\template.txt infer.model=flakey
~~~
