import asyncio
from datetime import datetime, timedelta, timezone
import os
import sys
import traceback
from typing import Any, Callable, List
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

        self._metadata = {
            "command": " ".join(sys.argv),
            "start": str(datetime.fromtimestamp(self._start, timezone.utc)),
            "concurrency": self._concurrency,
            "pipeline": {
                "name": pipeline_spec.name,
                "config": self._pipeline.get_config(),
            },
        }

        sha = get_git_sha()
        edits = get_current_edits() if sha else None
        if sha:
            self._metadata["sha"] = sha
        if edits:
            self._metadata["edits"] = edits

    async def process_all_cases(self, cases, progress, completed):
        # TODO: validation should be done when cases are loaded.
        validate_cases(cases)
        id = uuid.uuid4()
        runlog = {
            "results": {},
            "metadata": self._metadata.copy(),
            "uuid": str(id),
        }

        try:
            #
            # Perform the run
            #
            semaphore = asyncio.Semaphore(self._concurrency)

            async def sem_task(case):
                async with semaphore:
                    return await self.process_one_case(case, completed)

            tasks = [sem_task(case) for case in cases]
            results = await asyncio.gather(*tasks)

            #
            # Gather and record post-run metadata
            #
            end = datetime.now().timestamp()
            elapsed = end - self._start
            runlog["metadata"]["end"] = str(datetime.fromtimestamp(end, timezone.utc))
            runlog["metadata"]["elapsed"] = str(timedelta(seconds=elapsed))
            runlog["results"] = results

        except Exception as e:
            runlog["metadata"]["exception"] = {
                "message": str(e),
                "traceback": traceback.format_exc(),
                "time": str(datetime.now(timezone.utc)),
            }
        finally:
            # TODO: This is a temporary fix to get around the fact that the progress bar doesn't
            # disappear when the task is completed. It just stops updating.
            if progress:
                progress.stop()
            return runlog

    async def process_one_case(
        self,
        case: dict[str, Any],
        completed: Callable | None = None,
        turn: int | None = None,
    ):
        return await process_one_case(case, self._dag, completed, turn)

    def diff_configs(self):
        return self._pipeline.diff_configs()


# TODO: consider pydantic validation of cases
# TODO: validation should be done by users of Director
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