"""
This module demonstrates the implementation of a simple pipeline using the gotaglio tools.
"""

from copy import deepcopy
import os
from rich.console import Console
from glom import glom
from rich.table import Table
from rich.text import Text
import sys
import tiktoken

# Add the parent directory to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gotaglio.tools.exceptions import ExceptionContext
from gotaglio.tools.helpers import IdShortener
from gotaglio.tools.main import main
from gotaglio.tools.models import Model
from gotaglio.tools.pipeline import (
    merge_configs,
    Pipeline,
    ensure_required_configs,
)
from gotaglio.tools.repair import Repair
from gotaglio.tools.shared import build_template, minimal_unique_prefix
from gotaglio.tools.templating import jinja2_template


class SamplePipeline(Pipeline):
    """
    SamplePipeline demonstrates a simple two-stage LLM pipeline.

    Attributes:
      _name (str): The name of the pipeline.
      _description (str): A brief description of the pipeline.
      _default_config (dict): Default configuration dictionaries for each pipeline stage.
      _registry: The Registry instance used for instantiating models
      _config (dict): The merged configuration dictionary.
      _template: The prompt template for the prepare stage, lazily instantiated.
      _model: The model for the infer stage, lazily instantiated.
      _tokenizer: The tokenizer used for encoding text.

    Methods:
      __init__(registry, config_patch, replace_config=False):
        Initializes the pipeline with the given Registry and configuration.

      stages():
        Defines and returns the pipeline stage functions.

      summarize(context):
        Summarizes the results of the pipeline execution.

      compare(a, b):
        Compares the results of two pipeline executions.
    """

    # The Pipeline abstract base class requires _name and _description.
    _name = "simple"
    _description = "An example pipeline for converting natural language to api calls."


    def __init__(self, registry, replacement_config, flat_config_patch):
        """
        Initialize the pipeline with the given Registry and configuration.

        Args:
          registry: The Registry instance to be used in the stages() method. 
            The Registry provides access to system resources such as models.
          config_patch: A dictionary containing configuration value overrides from the command line.
          replace_config (bool): If True, replace the default config with config_patch entirely.
            If False, merge config_patch with the default config. Used when rerunning a case from
            a structure log.

        Attributes:
          _registry: Stores the Registry instance for later use.
          _config: The merged configuration dictionary.
          _template: Lazily instantiated template, initially set to None.
          _model: Lazily instantiated model, initially set to None.
          _tokenizer: The GPT-4o tokenizer loaded with the "cl100k_base" encoding.
        """
        # Save registry here for later use in the stages() method.
        self._registry = registry

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
        default_config = {
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
        super().__init__(default_config, replacement_config, flat_config_patch)


        # Construct and register some model mocks, specific to this pipeline.
        Flakey(registry, {})
        Perfect(registry, {})
        Parrot(registry, {})


    def stages(self):
        # # Perform some setup here so that any errors encountered
        # # are caught before running the cases.
        # with ExceptionContext(f"Pipeline '{self._name}' configuring stages."):
        #
        # Initialize objects used by the pipeline stages.
        #

        # Compile the jinja2 template used in the infer stage.
        template = build_template(
            self.config(),
            "prepare.template",
            "prepare.template_text",
        )

        # Instantiate the model for the infer stage.
        model = self._registry.model(glom(self.config(), "infer.model.name"))

        #
        # Define the pipeline stage functions
        #

        async def prepare(context):
            messages = [
                {"role": "system", "content": await template(context)},
                {"role": "user", "content": context["case"]["user"]},
            ]

            return messages

        async def infer(context):
            return await model.infer(context["stages"]["prepare"], context)

        async def extract(context):
            with ExceptionContext(f"Extracting numerical answer from LLM response."):
                return float(context["stages"]["infer"])

        async def assess(context):
            return context["stages"]["extract"] - context["case"]["answer"]

        return {
            "prepare": prepare,
            "infer": infer,
            "extract": extract,
            "assess": assess,
        }

    def summarize(self, context):
        if len(context) == 0:
            print("No results.")
        else:
            short_id = IdShortener(context["results"], "uuid")

            table = Table(title=f"Summary for {context['uuid']}")
            table.add_column("id", justify="right", style="cyan", no_wrap=True)
            table.add_column("run", style="magenta")
            table.add_column("score", justify="right", style="green")
            table.add_column("keywords", justify="left", style="green")

            total_count = len(context)
            complete_count = 0
            passed_count = 0
            failed_count = 0
            error_count = 0
            for result in context["results"]:
                id = short_id(result)
                # id = result["case"]["uuid"][:uuid_prefix_len]
                succeeded = result["succeeded"]
                cost = result["stages"]["assess"] if succeeded else None

                if succeeded:
                    complete_count += 1
                    if cost == 0:
                        passed_count += 1
                    else:
                        # Cost is None or a non-zero number
                        failed_count += 1
                else:
                    error_count += 1

                complete = (
                    Text("COMPLETE", style="bold green")
                    if succeeded
                    else Text("ERROR", style="bold red")
                )
                cost_text = "" if cost == None else f"{cost:.2f}"
                score = (
                    Text(cost_text, style="bold green")
                    if cost == 0
                    else Text(cost_text, style="bold red")
                )
                keywords = (
                    ", ".join(sorted(result["case"]["keywords"]))
                    if "keywords" in result["case"]
                    else ""
                )
                table.add_row(id, complete, score, keywords)
            console = Console()
            console.print(table)
            console.print()
            console.print(f"Total: {total_count}")
            console.print(
                f"Complete: {complete_count}/{total_count} ({(complete_count/total_count)*100:.2f}%)"
            )
            console.print(
                f"Error: {error_count}/{total_count} ({(error_count/total_count)*100:.2f}%)"
            )
            console.print(
                f"Passed: {passed_count}/{complete_count} ({(passed_count/total_count)*100:.2f}%)"
            )
            console.print(
                f"Failed: {failed_count}/{complete_count} ({(failed_count/total_count)*100:.2f}%)"
            )
            console.print()

    def format(self, context):
        # Load the GPT-4o tokenizer
        if not self:
            self._tokenizer = tiktoken.get_encoding("cl100k_base")

        if len(context) == 0:
            print("No results.")
        else:
            print("TODO: format()")
            for result in context["results"]:
                if result["succeeded"]:
                    print(f"Result: {result['stages']['infer']}")
                    print(
                        f"Output tokens : {len(self._tokenizer.encode(result['stages']['infer']))}"
                    )
                else:
                    print(f"Error: {result['exception']['message']}")
                    # print(f"Inference: {result['stages']['infer']}")
                    print(f"Traceback: {result['exception']['traceback']}")
                    print(f"Time: {result['exception']['time']}")

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

    def __init__(self, registry, configuration):
        self._counter = -1
        registry.register_model("flakey", self)

    async def infer(self, messages, context=None):
        self._counter += 1
        if self._counter % 3 == 0:
            return f'{context["case"]["answer"]}'
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

    def __init__(self, registry, configuration):
        registry.register_model("parrot", self)

    async def infer(self, messages, context=None):
        return f'{messages[-1]["role"]} says "{messages[-1]["content"]}"'

    def metadata(self):
        return {}


class Perfect(Model):
    """
    A mock model class that always returns the expected answer
    from context["case"]["turns"][-1]["expected"]
    """

    def __init__(self, registry, configuration):
        registry.register_model("perfect", self)

    async def infer(self, messages, context=None):
        return f'{context["case"]["answer"]}'

    def metadata(self):
        return {}


def go():
    main([SamplePipeline])


if __name__ == "__main__":
    go()
