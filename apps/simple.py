"""
This module demonstrates the implementation of a simple pipeline using the gotaglio tools.
"""

from copy import deepcopy
import json
import os
from rich.console import Console
from glom import glom
from rich.table import Table
from rich.text import Text
import sys
import tiktoken

# Add the parent directory to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gotaglio.tools.exceptions import ExceptionContext
from gotaglio.tools.main import main
from gotaglio.tools.models import Model
from gotaglio.tools.pipelines import (
    build_template,
    merge_configs,
    Pipeline,
    ensure_required_configs,
)
from gotaglio.tools.repair import Repair
from gotaglio.tools.shared import minimal_unique_prefix
from gotaglio.tools.templating import jinja2_template


class SamplePipeline(Pipeline):
    """
    SamplePipeline demonstrates a simple two-stage LLM pipeline.
    
    Attributes:
      _name (str): The name of the pipeline.
      _description (str): A brief description of the pipeline.
      _default_config (dict): Default configuration dictionaries for each pipeline stage.
      _runner: The runner instance used for executing the pipeline stages.
      _config (dict): The merged configuration dictionary.
      _template: The prompt template for the prepare stage, lazily instantiated.
      _model: The model for the infer stage, lazily instantiated.
      _tokenizer: The tokenizer used for encoding text.
    
    Methods:
      __init__(runner, config_patch, replace_config=False):
        Initializes the ApiPipeline with the given runner and configuration.
      
      stages():
        Defines and returns the pipeline stage functions.
      
      summarize(context):
        Summarizes the results of the pipeline execution.
      
      compare(a, b):
        Compares the results of two pipeline executions.
    """

    # The Pipeline abstract base class requires _name and _description.
    _name = "api"
    _description = "An example pipeline for converting natural language to api calls."

    # Dictionary of default configuration dicts for each pipeline stage.
    # The structure and interpretation of each configuration dict is determined
    # by the corresponding pipeline stage.
    #
    # A value of None indicates that the value must be provided on the command
    # line.
    #
    # There is no requirement to define a configuration dict for each stage.
    # It is the implementation of the pipeline that determines which stages
    # require configuration dicts.
    _default_config = {
        "prepare": {"template": None},
        "infer": {
            "model": {
                "name": None,
                "settings": {
                    "max_tokens": 800,
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "frequency_penalty": 0,
                    "presence_penalty": 0,
                },
            }
        },
    }

    def __init__(self, runner, config_patch, replace_config=False):
        """
        Initialize the pipeline with the given runner and configuration.

        Args:
          runner: The runner instance to be used in the stages() method. The runner provides
            access to system resources such as models.
          config_patch: A dictionary containing configuration value overrides from the command line.
          replace_config (bool): If True, replace the default config with config_patch entirely. 
            If False, merge config_patch with the default config. Used when rerunning a case from
            a structure log.

        Attributes:
          _runner: Stores the runner instance for later use.
          _config: The merged configuration dictionary.
          _template: Lazily instantiated template, initially set to None.
          _model: Lazily instantiated model, initially set to None.
          _tokenizer: The GPT-4o tokenizer loaded with the "cl100k_base" encoding.
        """
        # Save runner here for later use in the stages() method.
        self._runner = runner

        # Update the default config with values provided on the command-line.
        self._config = merge_configs(self._default_config, config_patch, replace_config)

        # Check the config for missing values.
        ensure_required_configs(self._name, self._config)

        # Construct and register some model mocks, specific to this pipeline.
        Parrot(self._runner, {})
        Flakey(self._runner, {})

        # Template and model are lazily instantiated in self.stages().
        # This allows us to use the pipeline for other purposes without
        # loading and compiling the prompt template.
        # TODO: should summarize() and compare() be static class methods?
        self._template = None
        self._model = None

        # Load the GPT-4o tokenizer
        self._tokenizer = tiktoken.get_encoding("cl100k_base")


    def stages(self):
        # Perform some setup here so that any errors encountered
        # are caught before running the cases.
        with ExceptionContext(f"Pipeline '{self._name}' configuring stages."):
            # Lazily build the prompt template for the prepare stage.
            if not self._template:
                self._template = build_template(
                    self._config,
                    "prepare.template",
                    "prepare.template_text",
                )

            # Lazily instantiate the model for the infer stage.
            if not self._model:
                self._model = self._runner.model(glom(self._config, "infer.model.name"))

        #
        # Define the pipeline stage functions
        #

        async def prepare(context):
            messages = [
                {"role": "system", "content": await self._template(context)},
                {"role": "user", "content": context["case"]["user"]},
            ]

            return messages

        async def infer(context):
            return await self._model.infer(context["stages"]["prepare"], context)

        return (
            self._config,
            {
                "prepare": prepare,
                "infer": infer,
            },
        )

    def summarize(self, context):
        if len(context) == 0:
            print("No results.")
        else:
            print("TODO: summarize()")
            for result in context["results"]:
                if result["succeeded"]:
                    print(f"Result: {result['stages']['infer']}")
                    print(f"Output tokens : {len(self._tokenizer.encode(result['stages']['infer']))}")
                else:
                    print(f"Error: {result['exception']['message']}")
                    # print(f"Inference: {result['stages']['infer']}")
                    print(f"Traceback: {result['exception']['traceback']}")
                    print(f"Time: {result['exception']['time']}")
            # uuids = [result["case"]["uuid"] for result in context["results"]]
            # uuid_prefix_len = max(minimal_unique_prefix(uuids), 3)

            # table = Table(title=f"Summary for {context['uuid']}")
            # table.add_column("id", justify="right", style="cyan", no_wrap=True)
            # table.add_column("run", style="magenta")
            # table.add_column("score", justify="right", style="green")
            # table.add_column("keywords", justify="left", style="green")

            # total_count = len(context)
            # complete_count = 0
            # passed_count = 0
            # failed_count = 0
            # error_count = 0
            # for result in context["results"]:
            #     id = result["case"]["uuid"][:uuid_prefix_len]
            #     succeeded = result["succeeded"]
            #     cost = result["stages"]["assess"]["cost"] if succeeded else None

            #     if succeeded:
            #         complete_count += 1
            #         if cost == 0:
            #             passed_count += 1
            #         else:
            #             failed_count += 1
            #     else:
            #         error_count += 1

            #     complete = (
            #         Text("COMPLETE", style="bold green")
            #         if succeeded
            #         else Text("ERROR", style="bold red")
            #     )
            #     cost_text = "" if cost == None else f"{cost:.2f}"
            #     score = (
            #         Text(cost_text, style="bold green")
            #         if cost == 0
            #         else Text(cost_text, style="bold red")
            #     )
            #     keywords = (
            #         ", ".join(sorted(result["case"]["keywords"]))
            #         if "keywords" in result["case"]
            #         else ""
            #     )
            #     table.add_row(id, complete, score, keywords)
            # console = Console()
            # console.print(table)
            # console.print()
            # console.print(f"Total: {total_count}")
            # console.print(
            #     f"Complete: {complete_count}/{total_count} ({(complete_count/total_count)*100:.2f}%)"
            # )
            # console.print(
            #     f"Error: {error_count}/{total_count} ({(error_count/total_count)*100:.2f}%)"
            # )
            # console.print(
            #     f"Passed: {passed_count}/{complete_count} ({(passed_count/total_count)*100:.2f}%)"
            # )
            # console.print(
            #     f"Failed: {failed_count}/{complete_count} ({(failed_count/total_count)*100:.2f}%)"
            # )
            # console.print()

    def compare(self, a, b):
        console = Console()
        console.print("TODO: compare()")

        # if a["uuid"] == b["uuid"]:
        #     console.print(f"Run ids are the same.\n")
        #     self.summarize(a)
        #     return

        # if a["metadata"]["pipeline"]["name"] != b["metadata"]["pipeline"]["name"]:
        #     console.print(
        #         f"Cannot perform comparison because pipeline names are different: A is '{
        #             a['metadata']['pipeline']['name']
        #         }', B is '{
        #             b['metadata']['pipeline']['name']
        #         }'"
        #     )
        #     return

        # a_cases = {result["case"]["uuid"]: result for result in a["results"]}
        # b_cases = {result["case"]["uuid"]: result for result in b["results"]}
        # a_uuids = set(a_cases.keys())
        # b_uuids = set(b_cases.keys())
        # both = a_uuids.intersection(b_uuids)
        # just_a = a_uuids - b_uuids
        # just_b = b_uuids - a_uuids

        # console.print(f"A: {a["uuid"]}")
        # console.print(f"B: {b["uuid"]}")
        # console.print("")
        # console.print(f"{len(just_a)} case{'s' if len(just_a) != 1 else ''} only in A")
        # console.print(f"{len(just_b)} case{'s' if len(just_b) != 1 else ''} only in B")
        # console.print(f"{len(both)} cases in both A and B")
        # console.print("")

        # # TODO: handle no results case
        # if len(both) == 0:
        #     console.print("There are no cases to compare.")
        #     console.print()
        #     # Fall through to print empty table

        # uuids = [uuid for uuid in both]
        # uuid_prefix_len = max(minimal_unique_prefix(uuids), 3)

        # table = Table(title=f"Comparison of {"A, B"}", show_footer=True)
        # table.add_column("id", justify="right", style="cyan", no_wrap=True)
        # table.add_column("A", justify="right", style="magenta")
        # table.add_column("B", justify="right", style="green")
        # table.add_column("keywords", justify="left", style="green")

        # rows = []
        # pass_count_a = 0
        # pass_count_b = 0
        # for uuid in both:
        #     (text_a, order_a) = format_case(a_cases[uuid])
        #     (text_b, order_b) = format_case(b_cases[uuid])
        #     keywords = ", ".join(sorted(a_cases[uuid]["case"].get("keywords", [])))
        #     if order_a == 0:
        #         pass_count_a += 1
        #     if order_b == 0:
        #         pass_count_b += 1
        #     rows.append(
        #         (
        #             (Text(uuid[:uuid_prefix_len]), text_a, text_b, keywords),
        #             order_b * 4 + order_a,
        #         )
        #     )
        # rows.sort(key=lambda x: x[1])
        # for row in rows:
        #     table.add_row(*row[0])

        # table.columns[0].footer = "Total"
        # table.columns[1].footer = Text(
        #     f"{pass_count_a}/{len(both)} ({(pass_count_a/len(both))*100:.0f}%)"
        # )
        # table.columns[2].footer = Text(
        #     f"{pass_count_b}/{len(both)} ({(pass_count_b/len(both))*100:.0f}%)"
        # )

        # console.print(table)
        # console.print()


# def format_row(uuid, keywords, text_a, order_a, text_b, order_b):
#     return (
#         Text(uuid),
#         text_a,
#         text_b,
#         Text(", ".join(sorted(keywords))),
#         order_b * 4 + order_a,
#     )


def format_case(result):
    if result["succeeded"]:
        if result["stages"]["assess"]["cost"] == 0:
            return (Text("passed", style="bold green"), 0)
        else:
            return (Text("failed", style="bold red"), 1)
    else:
        return (Text("error", style="bold red"), 2)


class Flakey(Model):
    """
    A mock model class that cycles through
      1. returning the expected answer
      2. returning "hello world"
      3. raising an exception
    """

    def __init__(self, runner, configuration):
        self._counter = -1
        runner.register_model("flakey", self)

    async def infer(self, messages, context=None):
        self._counter += 1
        if self._counter % 3 == 0:
            return f'{messages[-1]["role"]} says "{messages[-1]["content"]}"'
        elif self._counter % 3 == 1:
            return "hello world"
        else:
            raise Exception("Flakey model failed")

    def metadata(self):
        return {}


class Parrot(Model):
    """
    A mock model class that always returns the expected answer
    from context["case"]["turns"][-1]["expected"]
    """

    def __init__(self, runner, configuration):
        runner.register_model("parrot", self)

    async def infer(self, messages, context=None):
        return f'{messages[-1]["role"]} says "{messages[-1]["content"]}"'

    def metadata(self):
        return {}


def go():
    main([ApiPipeline])


if __name__ == "__main__":
    go()


