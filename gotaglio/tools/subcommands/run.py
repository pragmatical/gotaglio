import asyncio
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
import uuid

from ..constants import default_concurrancy
from ..shared import apply_patch, parse_key_value_args, read_json_file


def run_pipeline(runner_factory, args):
    cases_file = args.cases
    pipeline_name = args.pipeline
    pipeline_config = apply_patch({}, parse_key_value_args(args.key_values))
    concurrency = args.concurrency or default_concurrancy
    id = uuid.uuid4()

    print(f"Run configuration")
    print(f"  id: {id}")
    print(f"  cases: {cases_file}")
    print(f"  pipeline: {pipeline_name}")
    for (k,v) in pipeline_config.items():
        print(f"    {k}: {v}")
    print(f"  concurrancy: {concurrency}")
    print("")

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

        # Configure pipeline
        pipeline_factory = runner.pipeline(pipeline_name)
        pipeline = pipeline_factory(runner, pipeline_config)

        x = asyncio.run(runner.go(id, cases, pipeline, progress, completed))
        results = x["results"]
        progress.update(task1, visible=False)

        exception = results["metadata"].get("exception", None)
        if exception:
            print(f"Exception prior to run: {exception["message"]}\n\n")
        else:
            pipeline.summarize(results)

    print(f'Results written to {x["log"]}')
