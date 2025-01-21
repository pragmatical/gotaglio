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

# Add the parent directory to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gotaglio.tools.exceptions import ExceptionContext
from gotaglio.tools.main import main
from gotaglio.tools.models import Model
from gotaglio.tools.pipelines import (
    build_template,
    merge_configs,
    Pipeline,
    validate_config,
)
from gotaglio.tools.repair import Repair
from gotaglio.tools.shared import minimal_unique_prefix
from gotaglio.tools.templating import jinja2_template


class SimplePipeline(Pipeline):
    # The Pipeline abstract base class requires _name and _description.
    _name = "simple"
    _description = "An example pipeline"

    # Dictionary of default configuration dicts for each pipeline stage.
    # The structure of each configuration dict is dictated by the corresponding
    # pipeline stage.
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
        # TODO: should should not be required to include empty dicts.
        "extract": {},
        "assess": {},
    }

    def __init__(self, runner, config_patch, replace_config=False):
        self._runner = runner

        # Update the default config with values provided on the command-line.
        self._config = merge_configs(self._default_config, config_patch, replace_config)

        # Check the config for missing values.
        validate_config(self._name, self._config)

        # Construct and register two model mocks, specific to this pipeline.
        Perfect(self._runner, {})
        Flakey(self._runner, {})

        # Template and model are lazily instantiated in self.stages().
        # This allows us to use the pipeline for other purposes without
        # loading and compiling the prompt template.
        # TODO: should summarize() and compare() be static class methods?
        self._template = None
        self._model = None

    def stages(self):
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

        async def prepare(result):
            messages = [
                {"role": "system", "content": await self._template(result)},
                {"role": "assistant", "content": "{\ni items: []\n}\n"},
            ]
            case = result["case"]
            for c in case["turns"][:-1]:
                messages.append({"role": "user", "content": c["query"]})
                messages.append(
                    {
                        "role": "assistant",
                        "content": json.dumps(c["expected"], indent=2),
                    }
                )
            messages.append({"role": "user", "content": case["turns"][-1]["query"]})

            return messages

        async def infer(result):
            return await self._model.infer(result["stages"]["prepare"], result)

        async def extract(result):
            with ExceptionContext(f"Extracting JSON from LLM response."):
                return json.loads(result["stages"]["infer"])

        async def assess(result):
            repair = Repair("id", "options", [], ["name"], "name")
            repair.resetIds()
            observed = repair.addIds(result["stages"]["extract"]["items"])
            expected = repair.addIds(result["case"]["turns"][-1]["expected"]["items"])
            return repair.diff(observed, expected)

        return (
            self._config,
            {
                "prepare": prepare,
                "infer": infer,
                "extract": extract,
                "assess": assess,
            },
        )

    def summarize(self, results):
        if len(results) == 0:
            print("No results.")
        else:
            uuids = [result["case"]["uuid"] for result in results["results"]]
            uuid_prefix_len = max(minimal_unique_prefix(uuids), 3)

            table = Table(title=f"Summary for {results['uuid']}")
            table.add_column("id", justify="right", style="cyan", no_wrap=True)
            table.add_column("run", style="magenta")
            table.add_column("score", justify="right", style="green")
            table.add_column("keywords", justify="left", style="green")

            total_count = len(results)
            complete_count = 0
            passed_count = 0
            failed_count = 0
            error_count = 0
            for result in results["results"]:
                id = result["case"]["uuid"][:uuid_prefix_len]
                succeeded = result["succeeded"]
                cost = result["stages"]["assess"]["cost"] if succeeded else None

                if succeeded:
                    complete_count += 1
                    if cost == 0:
                        passed_count += 1
                    else:
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

    def compare(self, a, b):
        console = Console()

        if a["uuid"] == b["uuid"]:
            console.print(f"Run ids are the same.\n")
            self.summarize(a)
            return

        if a["metadata"]["pipeline"]["name"] != b["metadata"]["pipeline"]["name"]:
            console.print(
                f"Cannot perform comparison because pipeline names are different: A is '{
                    a['metadata']['pipeline']['name']
                }', B is '{
                    b['metadata']['pipeline']['name']
                }'"
            )
            return

        a_cases = {result["case"]["uuid"]: result for result in a["results"]}
        b_cases = {result["case"]["uuid"]: result for result in b["results"]}
        a_uuids = set(a_cases.keys())
        b_uuids = set(b_cases.keys())
        both = a_uuids.intersection(b_uuids)
        just_a = a_uuids - b_uuids
        just_b = b_uuids - a_uuids

        console.print(f"A: {a["uuid"]}")
        console.print(f"B: {b["uuid"]}")
        console.print("")
        console.print(f"{len(just_a)} case{'s' if len(just_a) != 1 else ''} only in A")
        console.print(f"{len(just_b)} case{'s' if len(just_b) != 1 else ''} only in B")
        console.print(f"{len(both)} cases in both A and B")
        console.print("")

        # TODO: handle no results case
        if len(both) == 0:
            console.print("There are no cases to compare.")
            console.print()
            # Fall through to print empty table

        uuids = [uuid for uuid in both]
        uuid_prefix_len = max(minimal_unique_prefix(uuids), 3)

        table = Table(title=f"Comparison of {"A, B"}", show_footer=True)
        table.add_column("id", justify="right", style="cyan", no_wrap=True)
        table.add_column("A", justify="right", style="magenta")
        table.add_column("B", justify="right", style="green")
        table.add_column("keywords", justify="left", style="green")

        rows = []
        pass_count_a = 0
        pass_count_b = 0
        for uuid in both:
            (text_a, order_a) = format_case(a_cases[uuid])
            (text_b, order_b) = format_case(b_cases[uuid])
            keywords = ", ".join(sorted(a_cases[uuid]["case"].get("keywords", [])))
            if order_a == 0:
                pass_count_a += 1
            if order_b == 0:
                pass_count_b += 1
            rows.append(
                (
                    (Text(uuid[:uuid_prefix_len]), text_a, text_b, keywords),
                    order_b * 4 + order_a,
                )
            )
        rows.sort(key=lambda x: x[1])
        for row in rows:
            table.add_row(*row[0])

        table.columns[0].footer = "Total"
        table.columns[1].footer = Text(
            f"{pass_count_a}/{len(both)} ({(pass_count_a/len(both))*100:.0f}%)"
        )
        table.columns[2].footer = Text(
            f"{pass_count_b}/{len(both)} ({(pass_count_b/len(both))*100:.0f}%)"
        )

        console.print(table)
        console.print()


def format_row(uuid, keywords, text_a, order_a, text_b, order_b):
    return (
        Text(uuid),
        text_a,
        text_b,
        Text(", ".join(sorted(keywords))),
        order_b * 4 + order_a,
    )


def format_case(result):
    if result["succeeded"]:
        if result["stages"]["assess"]["cost"] == 0:
            return (Text("passed", style="bold green"), 0)
        else:
            return (Text("failed", style="bold red"), 1)
    else:
        return (Text("error", style="bold red"), 2)


class Perfect(Model):
    """
    A mock model class that always returns the expected answer
    from context["case"]["turns"][-1]["expected"]
    """

    def __init__(self, runner, configuration):
        runner.register_model("perfect", self)

    async def infer(self, messages, context=None):
        return json.dumps(context["case"]["turns"][-1]["expected"])

    def metadata(self):
        return {}


class Flakey(Model):
    """
    A mock model class that sometimes returns the expected answer
    from context["case"]["turns"][-1]["expected"]. Other times it
    returns a bogus answer.
    """

    def __init__(self, runner, configuration):
        self._call_count = 0
        runner.register_model("flakey", self)

    async def infer(self, messages, context=None):
        expected = deepcopy(context["case"]["turns"][-1]["expected"])
        if self._call_count == 0:
            self._call_count += 1
            return "some text that is not json"
        if self._call_count % 2 == 0:
            expected["items"].append({"quantity": 123, "name": "foobar"})
        self._call_count += 1
        return json.dumps(expected)

    def metadata(self):
        return {}


def go():
    main([SimplePipeline])


if __name__ == "__main__":
    go()
