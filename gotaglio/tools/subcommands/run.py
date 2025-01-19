import asyncio
import json
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
import time

from ..shared import parse_key_value_args


def run_pipeline(runner_factory, args):
    cases_file = args.cases
    pipeline = args.pipeline
    config = parse_key_value_args(args.key_values)
    concurrency = args.concurrency or 2
    print(f"Running pipeline '{pipeline}' with concurrency {concurrency}...")

    runner = runner_factory()
    try:
        with open(cases_file, "r") as file:
            cases = json.load(file)
    except FileNotFoundError:
        raise ValueError(f"File {cases_file} not found.")
    except json.JSONDecodeError:
        raise ValueError(f"Error decoding JSON from file {cases_file}.")

    with Progress(
        SpinnerColumn(),
        *Progress.get_default_columns(),
        TimeElapsedColumn(),
        transient=True,
    ) as progress:
        task1 = progress.add_task("[red]Processing...", total=len(cases))

        def completed():
            progress.update(task1, advance=1)

        x = asyncio.run(runner.go(cases, pipeline, config, progress, completed))
        # Console().clear()
        progress.update(task1, visible=False)
        # progress.update(task1, completed=len(cases)+ 1)
        time.sleep(20)

    print(f'Results written to {x["log"]}')
