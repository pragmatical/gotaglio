# GoTaglio

GoTaglio is a lightweight python toolbox for creating ML pipelines for model evaluation and case labeling. Its goal is to accelerate the Applied Science inner loop by allowing principled experimentation to start informally on an engineer's machine in minutes.

GoTaglio includes the following key elements:
* Ability to rapidly define and run end-to-end ML pipelines.
* Automatic logging and organization of information about runs.
* The ability to rerun an earlier experiment with small changes.
* Structured logging to facilitate run analysis, comparing runs and tracking key metrics over time as the pipeline evolves.
* A python library that can be accessed from [Jupyter notebooks](https://jupyter.org/).
* A command-line tool to simplify common operations.
* [COMMING SOON] A web-based tool for oragnizing and labeling cases.

GoTaglio is designed to be very low friction. It is kind of like your thumb drive, loaded with all your tools, that will work in any Python environment.
* It does not require cloud deployment. All that is needed are model endpoints and credentials to access them.
* It can be used in cloud environments like [AzureML](https://azure.microsoft.com/en-us/products/machine-learning) or with frameworks like [mlflow](https://mlflow.org/).
* Pipeline code can be incorporated into production systems.

## Using GoTaglio

### Installing GoTaglio
GoTaglio is a python package that can be installed in your python environment.

Installing with [pip](https://pip.pypa.io/en/stable/):
~~~bash
pip install git+https://github.com/MikeHopcroft/gotaglio
~~~

Installing with [poetry](https://python-poetry.org/):
~~~bash
poetry add git+https://github.com/MikeHopcroft/gotaglio
~~~

### Configuring GoTaglio

See the documentation on [configuring models](documentation/models.md).

Create a `models.json` file:
~~~json
[
  {
    "name": "phi3",
    "description": "Phi-3 medium 128k",
    "type": "AZURE_AI",
    "endpoint": <ENDPOINT>,
    "key": "From .credentials.json"
  },
  {
    "name": "gpt3.5",
    "description": "GPT-3.5-turbo 16k",
    "type": "AZURE_OPEN_AI",
    "endpoint": <ENDPOINT>,
    "deployment": "gpt-35-turbo-16k-0613",
    "key": "From .credentials.json",
    "api": "2024-07-01-preview"
  },
  {
    "name": "gpt4o",
    "description": "gpt-4o-2024-11-20",
    "type": "AZURE_OPEN_AI",
    "endpoint": <ENDPOINT>,
    "deployment": "gpt-4o-2024-11-20",
    "key": "From .credentials.json",
    "api": "2024-08-01-preview"
  }
]
~~~

Create a `.credentials.json` file. There should be one
model-key pair for each model in models.json. Note that `.credentials.json` is .gitignored to prevent accidentally
committing credentials.
~~~json
{
  "phi3": <PHI3 KEY>,
  "gpt3.5": <GPT 3.5 KEY>,
  "gpt4o": <GPT 4o KEY>
}
~~~

### Implementing a pipeline

See the documentation on [implementing a pipeline](documentation/pipelines.md).

Import into python source files:
~~~python
from gotaglio import main
~~~

## Building GoTaglio

1. Verify you have python version >=3.12. Note that 3.13 may not be supported yet.
1. `pip install poetry` outside of any virtual environment
1. `git clone https://github.com/MikeHopcroft/gotaglio`
1. `cd gotaglio`
1. `python -m venv .venv`
1. `.venv\Scripts\activate`
1. `poetry install --no-root`

## Configuring Gotaglio

TODO: coming soon

## Running GoTaglio

You can use the `gotag` command to run the built-in restaurant menu pipeline demo.

~~~sh
% gotag
usage: gotag [-h] {add-ids,compare,help,history,models,pipelines,rerun,run,summarize} ...

A tool for managing and running ML pipelines.

positional arguments:
  {add-ids,compare,help,history,models,pipelines,rerun,run,summarize}
                        Subcommands
    add-ids             Add uuids to a suite
    compare             Compare two or more label sets
    help                Show help for gotaglio commands
    history             Show information about recent runs
    models              List available models
    pipelines           List available pipelines
    rerun               Rerun an experiment with modifications.
    run                 Run a named pipeline
    summarize           Summarize a run

options:
  -h, --help            show this help message and exit
~~~

Here's an example session that exercises most of the subcommands.

~~~sh
TODO: DEMO SESSION
~~~

## Gotaglio Configuration/Authentication

* models.json
* credentials.json

## Gotaglio Principles

* Everything is logged
* Logs contain most information needed to reproduce a result.
* One can easily rerun an experiment with different parameters.
* File and case naming convention
* Keywords/tags on cases
* Pipeline errors are tracked and used for evaluation

## Gotaglio Concepts

* Suite - a suite is a list of cases to be run through the pipeline.
* Case - a case specifies the user input and other contextual information for starting the pipeline and it can also contain expected results for use by an evaluation stage.
* Context - a Context records everything about a case as it moves through a pipeline. It has all of the configuration information for the pipeline and it stores the output of each stage and information about errors.
* Pipline - a pipeline is a user-defined set of processing stages. Typical stages include
  * a **preparation stage** that uses templating to form the system prompt and compose it with chat context and user input.
  * an **inference stage** the invokes the model
  * an **extraction stage** that parses or otherwise transforms the output of the model
  * an **evaluation stage** that produces a vector of score componets for the result
* Stage - a stage processes the output of earlier stages to produce its own output for use by later stages. The output of each stage is stored in the context.
* Model - a wrapper for an external AI model. Holds configuration data and handles network calls and authentication.
* Runlog - the runlog stores the pipeline configuration along with the contexts associated with each case in the suite.

## Implementing a Pipeline

Steps:

* Your pipeline should extend the Pipeline abstract base class.
  * _name
  * _description
  * stages() method returns tuple of (configuration, dict of stage functions)
  * summarize()
  * compare()

### Pipeline.stages()

### Pipeline.summarize()

### Pipeline.compare()

### Mock models

~~~sh
python apps\example.py run data\small.json simple prepare.template=data\template.txt infer.model.name=flakey
python apps\example.py run data\small.json simple prepare.template=data\template.txt infer.model.name=perfect
python apps\example.py run data\small.json simple prepare.template=data\template.txt infer.model.name=gpt3.5
python apps\example.py run data\small.json simple prepare.template=data\template.txt infer.model.name=phi3

python apps\example.py rerun LATEST infer.model.name=flakey
~~~


~~~
(.venv) C:\git\llm-tools\gotaglio>doskey /history
python apps\example.py rerun daeb infer.model.name=gpt3.5
start logs\bb1456a4-0c04-4ed8-a09a-65f638b5f6f6.json
python apps\example.py rerun daeb infer.model.name=flakey
python apps\example.py rerun dae infer.model.name=flakey
python apps\example.py rerun daeb infer.model.name=flakey
python apps\example.py history
python apps\example.py rerun LATEST infer.model.name=flakey
python apps\example.py rerun LATEST infer.model.name=flakey -concurrency 5      
python apps\example.py rerun LATEST infer.model.name=flakey --concurrency 5     
start logs\44f56665-80d7-4255-8716-a42a022b79e6.json
python apps\example.py rerun LATEST infer.model.name=flakey --concurrency 5     
python apps\example.py pipelines        
python apps\example.py models
python apps\example.py rerun LATEST infer.model.name=flakey
python apps\example.py rerun LATEST infer.model=flakey
git status
python apps\example.py rerun LATEST infer.model.name=flakey
git statuslogs\\729ce0d1-0afc-40a8-874d-fb30b9ebe1e4.jsonlogs\\729ce0d1-0afc-40a8-874d-fb30b9ebe1e4.jsonlogs\\729ce0d1-0afc-40a8-874d-fb30b9ebe1e4.jsonstart logs\729ce0d1-0afc-40a8-874d-fb30b9ebe1e4.json
start logs\729ce0d1-0afc-40a8-874d-fb30b9ebe1e4.json
python apps\example.py rerun LATEST infer.model.name=flakey
python apps\example.py run data\small.json simple prepare.template=data\template.txt infer.model.name=perfect
python apps\example.py rerun LATEST infer.model.name=flakey
start logs\2c44c827-3899-4612-9dc3-315dc58d3314.json
python apps\example.py summarize LATEST 
python apps\example.py summarize 2c44   
python apps\example.py summarize latest 
python apps\example.py history
python apps\example.py compare 917 2c4  
python apps\example.py help compare 917 2c4
python apps\example.py rerun 917 infer.model.name=flakey
python apps\example.py compare 917 043  
python apps\example.py compare 917 2c4  
python apps\example.py summarize 917    
python apps\example.py summarize 043    
python apps\example.py compare 917 043  
python apps\example.py help compare     
python apps\example.py compare 917 043
python apps\example.py compare 917 latest
python apps\example.py compare 917 917
python apps\example.py compare 917 latest
python apps\example.py compare 917 043
python apps\example.py compare 043 917
mkdir ..\gotaglio-web
python apps\example.py help
python apps\example.py help run
python apps\example.py help rerun
python apps\example.py help run
doskey /history

python apps\menu.py run data\menu\small.json menu prepare.template=data\menu\template.txt infer.model.name=gpt4o

~~~

