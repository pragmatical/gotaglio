# Cloning to your Local Workstation

Remember that you can skip all the steps below if you instead use the provided devcontainer in codespaces. Read more [here](./codespaces.md)

## Prerequisites

`GoTaglio` requires [python](https://www.python.org/) version 3.12 or greater. ***It will not work on 3.11***. Also note that we ***strongly recommend*** using a virtual environment and locating that virtual environment in the `.venv` folder at the root of the repo. Please note also that `gotaglio` is intended to work with [poetry](https://python-poetry.org/) rather than [pip](https://pip.pypa.io/en/stable/).

Before continuing verify that your shell can access `python` and `pip`, and that there is no virtual environment active:

~~~sh
% python --version
Python 3.12.9

% pip 24.3.1 from C:\Users\name\AppData\Local\Programs\Python\Python312\Lib\site-packages\pip (python 3.12)

% echo %VIRTUAL_ENV%
%VIRTUAL_ENV%
~~~

If a virtual environment had been active you would have seen something like:
~~~sh
% echo %VIRTUAL_ENV%
C:\git\llm-tools\gotaglio\.venv
~~~

## Cloning the repo
~~~sh
git clone https://github.com/MikeHopcroft/gotaglio.git
cd gotaglio
~~~

## Configuring the environment

The easiest way to configure the environment is to run the script used by the [devcontainer](https://docs.github.com/en/codespaces/setting-up-your-project-for-codespaces/adding-a-dev-container-configuration/introduction-to-dev-containers). Run this script from the root of the repo.

Linux:
~~~sh
. ./devcontainer/setup.sh
~~~

Windows:
~~~sh
./devcontainer/setup.bat
~~~

If you want to configure manually do the following steps:
~~~sh
% pip install poetry
% python -m venv .venv
% .venv\Scripts\Activate
% poetry install
~~~

Note in the above steps that [poetry](https://python-poetry.org/) must be install globallly, not in the virtual environment.

## Verifying the environment
Test with the `gotag` command:

~~~sh
% gotag help
usage: gotag [-h] {add-ids,compare,help,history,models,pipelines,rerun,run,format,summarize} ...

A tool for managing and running ML pipelines.

positional arguments:
  {add-ids,compare,help,history,models,pipelines,rerun,run,format,summarize}
                        Subcommands
    add-ids             Add uuids to a suite
    compare             Compare two or more label sets
    help                Show help for gotaglio commands
    history             Show information about recent runs
    models              List available models
    pipelines           List available pipelines
    rerun               Rerun an experiment with modifications.
    run                 Run a named pipeline
    format              Pretty print a run
    summarize           Summarize a run

options:
  -h, --help            show this help message and exit
~~~

You are now ready to run samples using mock models.

From here, you can continue with the [samples tutorial](./samples.md) or your can go on to [configuring external model endpoints](./models.md).