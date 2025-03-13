# Cloning to your Local Workstation

* Ensure you have python version 3.12 or greater.
* Ensure you have pip.

~~~sh
git clone https://github.com/MikeHopcroft/gotaglio.git
cd gotaglio
. ./devcontainer/setup.sh
~~~

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