# from colorama import Fore, Back, Style, init
import json
import os
from rich.console import Console
from glom import assign, glom
from rich.table import Table
from rich.text import Text
import sys

# Add the parent directory to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gotaglio.tools.main import main
from gotaglio.tools.pipelines import Pipeline
from gotaglio.tools.repair import Repair
from gotaglio.tools.shared import (
    flatten_dict,
    merge_dicts,
    minimal_unique_prefix,
    read_text_file,
)
from gotaglio.tools.templating import jinja2_template, load_template


def load(parameter):
    return lambda config: read_text_file(config[parameter])


def optional():
    pass


class SimplePipeline(Pipeline):
    _default_config = {
        "name": "simple",
        "stages": {
            "prepare": {"template": None, "template_text": optional},
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
            "extract": {},
            "assess": {},
        },
    }

    def __init__(self, runner, config_patch):
        self._config = merge_dicts(self._default_config, {"stages": config_patch})
        settings = flatten_dict(self._config["stages"])
        for k, v in settings.items():
            if v is None:
                raise ValueError(f"{self._default_config['name']} pipeline: missing '{k}' parameter.")
        # self._name = "simple"
        self._runner = runner

        # # Template is lazily loaded in self.stages()
        # if "template" not in self._config:
        #     raise ValueError(
        #         f"{self._name} pipeline: missing 'template=<filename>' parameter."
        #     )
        # self._template_file = self._config["template"]
        self._template = None
        # self._template_text = None

        #
        # Lookup the model
        #
        # if "model" not in config:
        #     raise ValueError("{self._name} pipeline: requires model=<name> parameter.")
        # self._model = runner.model(config["model"])
        self._model = None

    def stages(self):
        try:
            # Lazily build the prompt template for the prepare stage.
            if not self._template:
                if not isinstance(glom(self._config, "stages.prepare.template_text"), str):
                #     pass
                # if glom(self._config, "stages.prepare.template_text") is None:
                    assign(
                        self._config,
                        "stages.prepare.template_text",
                        read_text_file(glom(self._config, "stages.prepare.template")),
                    )
                self._template = jinja2_template(
                    glom(self._config, "stages.prepare.template_text")
                )

            # Lazily lookup the model for the infer stage.
            if not self._model:
                self._model = self._runner.model(glom(self._config, "stages.infer.model"))
                # if not self._config[]
                # (self._template_text, self._template) = load_template(
                #     self._config["template"]
                # )
        except Exception as e:
            raise ValueError(f"{self._default_config['name']} pipeline: {e}")

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
            return await self._model.infer(result["stages"]["prepare"])

        async def extract(result):
            try:
                return json.loads(result["stages"]["infer"])
            except json.JSONDecodeError as m:
                raise ValueError(f"Error decoding JSON: {m}")

        async def assess(result):
            repair = Repair("id", "options", [], ["name"], "name")
            repair.resetIds()
            observed = repair.addIds(result["stages"]["extract"]["items"])
            expected = repair.addIds(result["case"]["turns"][-1]["expected"]["items"])
            return repair.diff(observed, expected)

        return {
            "prepare": prepare,
            "infer": infer,
            "extract": extract,
            "assess": assess,
        }

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

    def metadata(self):
        # NOTE: WARNING: this method cannot be called before stages(). Perhaps make a return value of stages()?
        return self._config
        # return {
        #     # "name": self._name,
        #     "config": self._config,
        #     # "template": self._template_text,
        # }


def go():
    main({"simple": SimplePipeline})


if __name__ == "__main__":
    go()
