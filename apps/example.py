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
        return {
            "name": self._name,
            "config": self._config,
            "template": self._template_text,
        }


def go():
    main({"simple": SimplePipeline})


if __name__ == "__main__":
    go()
