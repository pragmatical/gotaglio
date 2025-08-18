import asyncio
from datetime import datetime, timedelta, timezone
from time import perf_counter
import json
import os
import sys
import traceback
from typing import Any, List
import uuid

from .constants import app_configuration
from .git_ops import get_current_edits, get_git_sha
from .helpers import IdShortener
from .models import register_models
from .pipeline import Pipeline, process_one_case
from .pipeline_spec import PipelineSpec
from .registry import Registry
from .shared import write_json_file


class Director:
    def __init__(
        self,
        pipeline_spec: PipelineSpec,
        cases: List[dict[str, Any]],
        replacement_config: dict[str, Any] | None,
        flat_config_patch: dict[str, Any],
        max_concurrency: int,
    ):
        # Wall-clock start for human-readable timestamps
        self._start_wall = datetime.now(timezone.utc)
        # Monotonic start for accurate elapsed timing
        self._start_perf = perf_counter()
        self._spec = pipeline_spec
        self._concurrency = max_concurrency

        registry = Registry()
        register_models(registry)

        self._pipeline = Pipeline(
            pipeline_spec, replacement_config, flat_config_patch, registry
        )
        self._dag = self._pipeline.get_dag()

        self._id = uuid.uuid4()
        self._output_file = os.path.join(
            app_configuration["log_folder"], f"{self._id}.json"
        )

        self._metadata = {
            "command": " ".join(sys.argv),
            # Record wall-clock timestamps (UTC) for readability
            "start": str(self._start_wall),
            "concurrency": self._concurrency,
            "pipeline": {
                "name": pipeline_spec.name,
                "config": self._pipeline.get_config(),
            },
        }
        self._results = {
            "results": {},
            "metadata": self._metadata,
            "uuid": str(self._id),
        }

        sha = get_git_sha()
        edits = get_current_edits() if sha else None
        if sha:
            self._metadata["sha"] = sha
        if edits:
            self._metadata["edits"] = edits

        validate_cases(cases)
        self._cases = cases

    async def process_all_cases(self, progress, completed):
        try:
            #
            # Perform the run
            #
            semaphore = asyncio.Semaphore(self._concurrency)

            async def sem_task(case):
                async with semaphore:
                    return await process_one_case(case, self._dag, completed)

            tasks = [sem_task(case) for case in self._cases]
            results = await asyncio.gather(*tasks)

            #
            # Gather and record post-run metadata
            #
            end_wall = datetime.now(timezone.utc)
            elapsed = perf_counter() - self._start_perf
            self._metadata["end"] = str(end_wall)
            self._metadata["elapsed"] = str(timedelta(seconds=elapsed))
            self._results["results"] = results

        except Exception as e:
            self._metadata["exception"] = {
                "message": str(e),
                "traceback": traceback.format_exc(),
                "time": str(datetime.now(timezone.utc)),
            }
        finally:
            # TODO: This is a temporary fix to get around the fact that the progress bar doesn't
            # disappear when the task is completed. It just stops updating.
            if progress:
                progress.stop()
            return self._results

    def write(self):
        # Write results to log file
        log_folder = app_configuration["log_folder"]
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)
        write_json_file(self._output_file, self._results)

        print(f"Results written to {self._output_file}")
        return {"log": self._output_file, "results": self._results}

    def summarize_results(self):
        # TODO: this is an example of code that doesn't use Registry.summaraize().
        # This is because the pipeline was already created in __init()__
        console = MakeConsole()
        self._pipeline.summarize(console, self._results)
        console.render()
        # print(f"Results written to {self._output_file}")


async def process_one_case(case, dag, completed):
    ExceptionContext.clear_context()
    start_wall = datetime.now(timezone.utc)
    start_perf = perf_counter()
    result = {
        "succeeded": False,
        # Wall-clock timestamps for readability
        "metadata": {"start": str(start_wall)},
        "case": case,
    # Stage return values go here (unchanged contract)
    "stages": {},
    # Internal per-stage timing store, used by dag.run_task();
    # will be merged into stages_detailed and removed before returning.
    "stage_metadata": {},
    # New: alongside each stage's value, include timing details.
    # stages_detailed[stage_name] = { "value": <stage result>, "start": ..., "end": ..., "elapsed": ..., "succeeded": ... }
    "stages_detailed": {},
    }
    try:
        await run_dag(dag, result)
    except Exception as e:
        result["exception"] = {
            "message": ExceptionContext.format_message(e),
            "traceback": traceback.format_exc(),
            "time": str(datetime.now(timezone.utc)),
        }
        return result

    end_wall = datetime.now(timezone.utc)
    if completed:
        completed()
    elapsed = perf_counter() - start_perf
    result["metadata"]["end"] = str(end_wall)
    result["metadata"]["elapsed"] = str(timedelta(seconds=elapsed))

    # Embed per-stage timing into each stage entry as an object with
    # fields: value, start, end, elapsed, succeeded. Preserve raw value shape
    # during execution; only transform after run_dag completes.
    try:
        stage_meta = result.get("stage_metadata", {})
        wrapped = {}
        for name, value in result.get("stages", {}).items():
            meta = stage_meta.get(name, {})
            entry = {"value": value}
            for k in ("start", "end", "elapsed", "succeeded"):
                if k in meta:
                    entry[k] = meta[k]
            wrapped[name] = entry
        result["stages"] = wrapped
    finally:
        # Remove internal timing store before returning
        if "stage_metadata" in result:
            try:
                del result["stage_metadata"]
            except Exception:
                pass
    result["succeeded"] = True
    return result
    def diff_configs(self):
        return self._pipeline.diff_configs()


def validate_cases(cases):
    if not isinstance(cases, list):
        raise ValueError("Cases must be a list.")

    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"Case {index} not a dictionary.")
        if "uuid" not in case:
            raise ValueError(f"Case {index} missing uuid.")

    # Instantiate the IdShortener to validate uuid text and check for duplicates.
    IdShortener([case["uuid"] for case in cases])
