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
~~~
