import asyncio
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from typing import Any, cast

from ..constants import app_configuration
from ..director import Director
from ..pipeline_spec import PipelineSpecs
from ..shared import (
    log_file_name_from_prefix,
    parse_key_value_args,
    read_data_file,
    read_json_file,
    write_log_file,
)
from ..summarize import summarize


def run_command(pipeline_specs: PipelineSpecs, args):
    cases_file = args.cases
    pipeline_name = args.pipeline
    flat_config_patch = parse_key_value_args(args.key_values)
    concurrency = args.concurrency or app_configuration["default_concurrancy"]

    pipeline_spec = pipeline_specs.get(pipeline_name)

    # TODO: remove this temporary cast once we get pydantic validation of the cases.
    cases = cast(Any, read_data_file(cases_file, False, False))

    # TODO: remove this cast after we validate or annotate the command-line arguments.
    director = Director(pipeline_spec, None, flat_config_patch, cast(int, concurrency))
    print(f"Run configuration")
    print(f"  cases: {cases_file}")
    print(f"  pipeline: {pipeline_name}")
    diff = director.diff_configs()
    lines = [f"    {k}: {v1} => {v2}" for k, v1, v2 in diff]
    print("\n".join(lines))
    print(f"  concurrancy: {concurrency}")
    print("")

    runlog = run_with_progress_bar(director, cases)

    write_log_file(runlog, chatty=True)
    summarize(pipeline_spec, runlog)


def rerun_command(pipeline_specs: PipelineSpecs, args):
    original_id = args.id
    log_file_name = log_file_name_from_prefix(original_id)
    log = read_json_file(log_file_name, False)
    metadata = log["metadata"]

    # TODO: remove this cast once the args are typed.
    concurrency = cast(
        int, args.concurrency or app_configuration["default_concurrancy"]
    )

    cases = [record["case"] for record in log["results"]]
    if "pipeline" not in metadata:
        raise Exception("No pipeline metadata found in results file")

    pipeline_name = metadata["pipeline"]["name"]
    pipeline_spec = pipeline_specs.get(pipeline_name)

    replacement_config = metadata["pipeline"]["config"]
    flat_config_patch = parse_key_value_args(args.key_values)

    # TODO: remove this cast after we validate or annotate the command-line arguments.
    director = Director(
        pipeline_spec,
        replacement_config,
        flat_config_patch,
        cast(int, concurrency),
    )

    print(f"Rerun configuration")
    print(f"  based on: {log["uuid"]}")
    print(f"  cases: {log_file_name}")
    print(f"  pipeline: {pipeline_name}")
    diff = director.diff_configs()
    lines = [f"    {k}: {v1} => {v2}" for k, v1, v2 in diff]
    print("\n".join(lines))
    print(f"  concurrancy: {concurrency}")
    print("")

    runlog = run_with_progress_bar(director, cases)

    write_log_file(runlog, chatty=True)
    summarize(pipeline_spec, runlog["results"])


def run_with_progress_bar(director: Director, cases):
    with Progress(
        SpinnerColumn(),
        *Progress.get_default_columns(),
        TimeElapsedColumn(),
        transient=True,
    ) as progress:
        task = progress.add_task("[red]Processing...", total=len(cases))

        def completed():
            progress.update(task, advance=1)

        runlog = asyncio.run(director.process_all_cases(cases, progress, completed))
        progress.update(task, visible=False)
        return runlog
