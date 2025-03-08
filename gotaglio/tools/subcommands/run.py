import asyncio
import json
import os
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
import uuid

from ..constants import default_concurrancy, log_folder

# from gotaglio.tools.pipelines import (
#     merge_configs,
#     ensure_required_configs,
# )
from ..runner import Director
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
    flat_config_patch = parse_key_value_args(args.key_values)
    concurrency = args.concurrency or default_concurrancy

    cases = read_json_file(cases_file, False)

    director = Director(
        runner_factory,
        pipeline_name,
        cases,
        None,
        flat_config_patch,
        concurrency,
    )

    print(f"Run configuration")
    print(f"  id: {director._id}")
    print(f"  cases: {cases_file}")
    print(f"  pipeline: {pipeline_name}")
    for k, v in flat_config_patch.items():
        print(f"    {k}: {v}")
    print(f"  concurrancy: {concurrency}")
    print("")

    run_with_progress_bar(director)
    # perform_run(runner_factory, pipeline_name, pipeline_config, concurrency, id, cases)

    director.write_results()
    director.summarize_results()


def rerun_pipeline(runner_factory, args):
    original_id = args.id
    log_file_name = log_file_name_from_prefix(original_id)
    log = read_json_file(log_file_name, False)
    metadata = log["metadata"]

    concurrency = args.concurrency or default_concurrancy

    cases = [record["case"] for record in log["results"]]
    if "pipeline" not in metadata:
        raise Exception("No pipeline metadata found in results file")

    pipeline_name = metadata["pipeline"]["name"]
    replacement_config = metadata["pipeline"]["config"]
    flat_config_patch = parse_key_value_args(args.key_values)

    director = Director(
        runner_factory,
        pipeline_name,
        cases,
        replacement_config,
        flat_config_patch,
        concurrency,
    )

    print(f"Rerun configuration")
    print(f"  based on: {log["uuid"]}")
    print(f"  id: {director._id}")
    print(f"  cases: {log_file_name}")
    print(f"  pipeline: {pipeline_name}")
    for k, v in flat_config_patch.items():
        print(f"    {k}: {v}")
    print(f"  concurrancy: {concurrency}")
    print("")

    run_with_progress_bar(director)

    director.write_results()
    director.summarize_results()



# def perform_run(
#     runner_factory, pipeline_name, config_patch, replace_config, concurrency, id, cases
# ):
#     # Configure pipeline
#     runner = runner_factory()
#     pipeline_factory = runner.pipeline(pipeline_name)
#     pipeline = pipeline_factory(runner)
#     # Want to run initialization code in pipeline.stages()
#     # before starting progress spinner.
#     stages = pipeline.stages()
#     config = pipeline._config

#     # # Update the default config with values provided on the command-line.
#     # config = merge_configs(pipeline._config, config_patch, replace_config)

#     # # Check the config for missing values.
#     # ensure_required_configs(pipeline._name, config)

#     # with ExceptionContext(f"Pipeline '{pipeline_name}' configuring stages."):
#     #     pass
#     # config = pipeline.on_before_run(runner)

#     with Progress(
#         SpinnerColumn(),
#         *Progress.get_default_columns(),
#         TimeElapsedColumn(),
#         transient=True,
#     ) as progress:
#         task1 = progress.add_task("[red]Processing...", total=len(cases))

#         def completed():
#             progress.update(task1, advance=1)

#         x = asyncio.run(
#             runner.go(
#                 id,
#                 cases,
#                 pipeline_name,
#                 stages,
#                 config,
#                 concurrency,
#                 progress,
#                 completed,
#             )
#         )
#         results = x["results"]
#         progress.update(task1, visible=False)

#         exception = results["metadata"].get("exception", None)
#         if exception:
#             print(f"Exception prior to run: {exception["message"]}\n\n")
#         else:
#             pipeline.summarize(results)

#     print(f'Results written to {x["log"]}')


async def perform_run2(
    runner_factory,
    pipeline_name,
    cases_file,
    flat_config_patch,
    replace_config,
    max_concurrency,
):
    director = Director(
        runner_factory,
        pipeline_name,
        cases_file,
        flat_config_patch,
        replace_config,
        max_concurrency,
    )

    with Progress(
        SpinnerColumn(),
        *Progress.get_default_columns(),
        TimeElapsedColumn(),
        transient=True,
    ) as progress:
        task1 = progress.add_task("[red]Processing...", total=len(director._cases))

        def completed():
            progress.update(task1, advance=1)

        x = asyncio.run(
            director.process_all_cases(progress, completed)
        )
        progress.update(task1, visible=False)

        # exception = results["metadata"].get("exception", None)
        # if exception:
        #     print(f"Exception prior to run: {exception["message"]}\n\n")
        # else:

    director.write_results()
    director.summarize_results()
    # print(f'Results written to {x["log"]}')

def run_with_progress_bar(
    director,
):
    with Progress(
        SpinnerColumn(),
        *Progress.get_default_columns(),
        TimeElapsedColumn(),
        transient=True,
    ) as progress:
        task1 = progress.add_task("[red]Processing...", total=len(director._cases))

        def completed():
            progress.update(task1, advance=1)

        x = asyncio.run(
            director.process_all_cases(progress, completed)
        )
        progress.update(task1, visible=False)
