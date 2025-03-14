# GoTaglio

`GoTaglio` is a lightweight python toolbox for creating ML pipelines for model evaluation and case labeling. Its goal is to accelerate the Applied Science inner-loop by allowing principled experimentation to start informally on an engineer's machine in minutes, while producing learnings and artifacts that scale through production.

`GoTaglio` is designed to be very low friction. It is kind of like a thumb drive, loaded with power tools, that will work in any Python environment.
* It does not require significant cloud infrastructure deployment. All that is needed are model endpoints and credentials to access them.
* It can be used in cloud environments like [AzureML](https://azure.microsoft.com/en-us/products/machine-learning) or with frameworks like [mlflow](https://mlflow.org/).
* Pipeline code can be incorporated into production systems.

`GoTaglio` includes the following key elements:
* Ability to rapidly define and run end-to-end ML pipelines.
* Automatic logging and organization of information about runs.
* The ability to rerun an earlier experiment with small changes introduced on the command-line.
* Structured logging to facilitate run analysis, comparing runs and tracking key metrics over time as the pipeline evolves.
* A python library that can be accessed from [Jupyter notebooks](https://jupyter.org/).
* A command-line tool to simplify common operations.
* [COMING SOON] A web-based tool for oragnizing and labeling cases.

## Try GoTaglio

GoTaglio comes with [several samples](documentation/samples.md) that run out-of-the-box with included LLM mocks or your LLM endpoints.

## Learn GoTaglio

Get an overview of key [GoTaglio concepts](documentation/concepts.md) such as
* configuration merging
* models
* pipelines
* structured logging

## Use GoTaglio

Learn how to [incorporate GoTaglio into your process](documentation/usage.md) as
* a command-line tool
* a [Jupyter notebook](https://jupyter.org/) enhancement
* a python library
