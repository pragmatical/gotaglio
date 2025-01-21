import asyncio
import json
import os
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
import uuid

from ..constants import default_concurrancy, log_folder
from ..shared import (
    apply_patch,
    flatten_dict,
    log_file_name_from_prefix,
    parse_key_value_args,
    read_json_file,
)


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
    for k, v in pipeline_config.items():
        print(f"    {k}: {v}")
    print(f"  concurrancy: {concurrency}")
    print("")

    cases = read_json_file(cases_file, False)
    perform_run(runner_factory, pipeline_name, pipeline_config, concurrency, id, cases)


def rerun_pipeline(runner_factory, args):
    original_id = args.id
    log_file_name = log_file_name_from_prefix(original_id)
    results = read_json_file(log_file_name, False)

    concurrency = args.concurrency or default_concurrancy
    id = uuid.uuid4()

    cases = [record["case"] for record in results["results"]]
    if "pipeline" not in results["metadata"]:
        raise Exception("No pipeline metadata found in results file")
    pipeline_name = results["metadata"]["pipeline"]["name"]
    original_config = results["metadata"]["pipeline"]["config"]
    pipeline_patches = parse_key_value_args(args.key_values)
    pipeline_config = apply_patch(original_config, pipeline_patches)

    print(f"Rerun configuration")
    print(f"  based on: {results["uuid"]}")
    print(f"  id: {id}")
    print(f"  cases: {log_file_name}")
    print(f"  pipeline: {pipeline_name}")

    a = flatten_dict(pipeline_config)
    for k, v in pipeline_patches.items():
        print(f"    {k}: {v}")
        
    print(f"  concurrancy: {concurrency}")
    print("")

    perform_run(runner_factory, pipeline_name, pipeline_config, concurrency, id, cases)


def perform_run(runner_factory, pipeline_name, pipeline_config, concurrency, id, cases):
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

        x = asyncio.run(runner.go(id, cases, pipeline, concurrency, progress, completed))
        results = x["results"]
        progress.update(task1, visible=False)

        exception = results["metadata"].get("exception", None)
        if exception:
            print(f"Exception prior to run: {exception["message"]}\n\n")
        else:
            pipeline.summarize(results)

    print(f'Results written to {x["log"]}')
