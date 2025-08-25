import asyncio
from datetime import datetime, timedelta, timezone
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
        self._start = datetime.now().timestamp()
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
            "start": str(datetime.fromtimestamp(self._start, timezone.utc)),
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
            end = datetime.now().timestamp()
            elapsed = end - self._start
            self._metadata["end"] = str(datetime.fromtimestamp(end, timezone.utc))
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