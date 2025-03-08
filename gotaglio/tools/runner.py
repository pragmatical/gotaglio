import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
import sys
import traceback
import uuid

from .constants import log_folder
from .exceptions import ExceptionContext
from .git import get_current_edits, get_git_sha
from .shared import format_list


async def process_one_case(case, stages, completed):
    ExceptionContext.clear_context()
    start = datetime.now().timestamp()
    result = {
        "succeeded": False,
        "metadata": {"start": str(datetime.fromtimestamp(start, timezone.utc))},
        "case": case,
        "stages": {},
    }
    try:
        for stage, func in stages.items():
            try:
                result["stages"][stage] = await func(result)
            except Exception as e:
                result["exception"] = {
                    "stage": stage,
                    "message": ExceptionContext.format_message(e),
                    "traceback": traceback.format_exc(),
                    "time": str(datetime.now(timezone.utc)),
                }
                return result
    except Exception as e:
        result["exception"] = {
            "message": ExceptionContext.format_message(e),
            "traceback": traceback.format_exc(),
            "time": str(datetime.now(timezone.utc)),
        }
        return result

    end = datetime.now().timestamp()
    if completed:
        completed()
    elapsed = end - start
    result["metadata"]["end"] = str(datetime.fromtimestamp(end, timezone.utc))
    result["metadata"]["elapsed"] = str(timedelta(seconds=elapsed))
    result["succeeded"] = True
    return result


class Runner:
    def __init__(self):
        self._models = {}
        self._pipelines = {}
        pass

    def register_model(self, name, model):
        if name in self._models:
            raise ValueError(f"Attempting to register duplicate model '{name}'.")
        self._models[name] = model

    def model(self, name):
        if name not in self._models:
            names = format_list([k for k in self._models.keys()])
            raise ValueError(
                f"Model '{name}' not found. Available models include {names}."
            )
        return self._models[name]

    def register_pipeline(self, pipeline):
        name = pipeline.name()
        if name in self._pipelines:
            raise ValueError(f"Attempting to register duplicate pipeline '{name}'.")
        self._pipelines[name] = pipeline

    def pipeline(self, name):
        if name not in self._pipelines:
            names = format_list([k for k in self._pipelines.keys()])
            raise ValueError(
                f"Pipeline '{name}' not found. Available pipelines include {names}."
            )
        return self._pipelines[name]

    # TODO: does summarize() really need to be in runner?
    def summarize(self, results):
        # TODO: checck that metadata.pipline exists
        # It probably exists because it is initialized in very early in
        # process_all_cases().
        pipeline_name = results["metadata"]["pipeline"]["name"]
        pipeline_config = results["metadata"]["pipeline"]["config"]
        pipeline_factory = self.pipeline(pipeline_name)
        pipeline = pipeline_factory(self, pipeline_config, {})
        pipeline.summarize(results)

    def format(self, results):
        # TODO: checck that metadata.pipline exists
        # It probably exists because it is initialized in very early in
        # process_all_cases().
        pipeline_name = results["metadata"]["pipeline"]["name"]
        pipeline_config = results["metadata"]["pipeline"]["config"]
        pipeline_factory = self.pipeline(pipeline_name)
        pipeline = pipeline_factory(self, pipeline_config, {})
        pipeline.format(results)

    # TODO: does summarize() need to be in runner?
    def compare(self, results_a, results_b):
        # TODO: check that metadata.pipline exists
        # It probably exists because it is initialized in very early in
        # process_all_cases().
        # TODO: check that both results are from the same pipeline
        pipeline_name = results_a["metadata"]["pipeline"]["name"]
        pipeline_config = results_a["metadata"]["pipeline"]["config"]
        pipeline_factory = self.pipeline(pipeline_name)
        pipeline = pipeline_factory(self, pipeline_config, {})
        pipeline.compare(results_a, results_b)


class Director:
    def __init__(
        self,
        runner_factory,
        pipeline_name,
        cases,
        replacement_config,
        flat_config_patch,
        max_concurrancy,
    ):
        self._start = datetime.now().timestamp()
        self._concurrancy = max_concurrancy
        self._pipeline_name = pipeline_name

        # self._runner = runner_factory()
        runner = runner_factory()
        pipeline_factory = runner.pipeline(pipeline_name)
        # config_patch = apply_patch({}, flat_config_patch)
        self._pipeline = pipeline_factory(runner, replacement_config, flat_config_patch)
        self._stages = self._pipeline.stages()
        self._config = self._pipeline.config()

        self._id = uuid.uuid4()
        self._output_file = os.path.join(log_folder, f"{self._id}.json")

        self._metadata = {
            "command": " ".join(sys.argv),
            "start": str(datetime.fromtimestamp(self._start, timezone.utc)),
            "concurrency": self._concurrancy,
            "pipeline": {"name": pipeline_name, "config": self._pipeline._config},
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

        self._cases = cases


    async def process_all_cases(self, progress, completed):
        try:
            #
            # Perform the run
            #
            semaphore = asyncio.Semaphore(self._concurrancy)

            async def sem_task(case):
                async with semaphore:
                    return await process_one_case(case, self._stages, completed)

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

    def write_results(self):
        # Write log
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)
        with open(self._output_file, "w") as f:
            json.dump(self._results, f, indent=2)

        return {"log": self._output_file, "results": self._results}

    def summarize_results(self):
        self._pipeline.summarize(self._results)
        print(f'Results written to {self._output_file}')
