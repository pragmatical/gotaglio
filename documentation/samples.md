# Sample Applications

Samples include
* [simple.py](../samples/simple/simple.py) - demonstration of a simple 4 stage linear pipeline that uses a language model as a calculator.
* [dag.py](../samples/dag/dag.py) - demonstration of a [directed acyclic graph](https://en.wikipedia.org/wiki/Directed_acyclic_graph) (DAG) pipeline.
* menu.py - a restaurant ordering demo

All of the samples are accessible via the `gotag` command.

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

~~~sh
% gotag pipelines
Available pipelines:
  dag: An example of a directed acyclic graph (DAG) pipeline.
  simple: An example pipeline for an LLM-based calculator.

% gotag models
Available models:
  phi3: Phi-3 medium 128k
  gpt3.5: GPT-3.5-turbo 16k
  gpt4o: gpt-4o-2024-11-20
~~~

~~~
% gotag help run
usage: gotag run [-h] [-c CONCURRENCY] pipeline cases [key_values ...]

positional arguments:
  pipeline              The name of the pipeline to run
  cases                 The name of a file with cases
  key_values            key=value arguments to configure pipeline

options:
  -h, --help            show this help message and exit
  -c CONCURRENCY, --concurrency CONCURRENCY
                        Maximum concurrancy for tasks
~~~

~~~sh
% gotag run simple samples/simple/cases.json prepare.template=samples/simple/template.txt infer.model.name=perfect
Run configuration
  id: d940443f-4869-45a7-9a98-4497cf8e539e
  cases: samples\simple\cases.json
  pipeline: simple
    prepare.template: PROMPT => samples\simple\template.txt
    infer.model.name: PROMPT => perfect
  concurrancy: 2

    Summary for d940443f-4869-45a7-9a98-4497cf8e539e                                                                                                 
┏━━━━━┳━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  id ┃ run      ┃ score ┃ keywords                     ┃
┡━━━━━╇━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ ed6 │ COMPLETE │  0.00 │ addition, p0                 │
│ e09 │ COMPLETE │  0.00 │ addition, multiplication, p0 │
│ e86 │ COMPLETE │  0.00 │ division, hexidecimal        │
│ d73 │ COMPLETE │  0.00 │ division, hexidecimal, fails │
└─────┴──────────┴───────┴──────────────────────────────┘

Total: 4
Complete: 4/4 (100.00%)
Error: 0/4 (0.00%)
Passed: 4/4 (100.00%)
Failed: 0/4 (0.00%)

Results written to logs\d940443f-4869-45a7-9a98-4497cf8e539e.json
~~~
