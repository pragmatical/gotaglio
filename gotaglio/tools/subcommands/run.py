import asyncio
import json
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
import time

from ..constants import default_concurrancy
from ..shared import apply_patch, parse_key_value_args, read_json_file


def run_pipeline(runner_factory, args):
    cases_file = args.cases
    pipeline_name = args.pipeline
    pipeline_config = apply_patch({}, parse_key_value_args(args.key_values))
    concurrency = args.concurrency or default_concurrancy

    print(f"Running pipeline '{pipeline_name}' with concurrency {concurrency}...")

    cases = read_json_file(cases_file, False)
    runner = runner_factory()

    with Progress(
        SpinnerColumn(),
        *Progress.get_default_columns(),
        TimeElapsedColumn(),
        transient=True,
    ) as progress:
        task1 = progress.add_task("[red]Processing...", total=len(cases))

        def completed():
            progress.update(task1, advance=1)

        x = asyncio.run(runner.go(cases, pipeline_name, pipeline_config, progress, completed))
        progress.update(task1, visible=False)
        # time.sleep(20)

    print(f'Results written to {x["log"]}')
