from colorama import Fore, Back, Style, init
import json
import os
from rich.console import Console
from rich.table import Table
from rich.text import Text
import sys

# Add the parent directory to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gotaglio.tools.main import main
from gotaglio.tools.pipelines import Pipeline
from gotaglio.tools.repair import Repair
from gotaglio.tools.shared import minimal_unique_prefix
from gotaglio.tools.templating import load_template


class SimplePipeline(Pipeline):
    def __init__(self, runner, config):
        self._config = config
        self._name = "simple"
        self._runner = runner

        # Template is lazily loaded in self.stages()
        if "template" not in self._config:
            raise ValueError(
                f"{self._name} pipeline: missing 'template=<filename>' parameter."
            )
        self._template_file = self._config["template"]
        self._template = None
        self._template_text = None

        #
        # Lookup the model
        #
        if "model" not in config:
            raise ValueError("{self._name} pipeline: requires model=<name> parameter.")
        self._model = runner.model(config["model"])

    def stages(self):
        try:
            if not self._template:
                (self._template_text, self._template) = load_template(
                    self._template_file
                )
        except Exception as e:
            raise ValueError(f"{self._name} pipeline: {e}")

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
            # repair.Repair('id', 'children', [], [], 'name')
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
        def cost(result):
            if result["succeeded"]:
                cost = result["stages"]["assess"]["cost"]
                return cost
            else:
                return None

        summary = [
            {
                "uuid": result["case"]["uuid"],
                "succeeded": result["succeeded"],
                "cost": cost(result),
            }
            for result in results["results"]
        ]
        if len(summary) == 0:
            print("No results.")
        else:
            uuids = [item["uuid"] for item in summary]
            uuid_prefix_len = max(minimal_unique_prefix(uuids), 3)

            table = Table(title=f"Summary for {results['uuid']}")
            table.add_column("id", justify="right", style="cyan", no_wrap=True)
            table.add_column("run", style="magenta")
            table.add_column("score", justify="right", style="green")
            table.add_column("keywords", justify="right", style="green")

            for item in summary:
                id = item["uuid"][:uuid_prefix_len]
                complete = Text("COMPLETE", style="bold green") if item["succeeded"] else Text("ERROR", style="bold red")
                cost = "" if item["cost"] == None else f"{item['cost']:.2f}"
                score = Text(cost, style="bold green") if item['cost'] == 0 else Text(cost, style="bold red")
                table.add_row(id, complete, score)
            console = Console()
            console.print(table)

    def metadata(self):
        return {
            "name": self._name,
            "config": self._config,
            "template": self._template_text,
        }


def go():
    main({"simple": SimplePipeline})


if __name__ == "__main__":
    go()
