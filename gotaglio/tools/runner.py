from .constants import log_folder
from .exceptions import ExceptionContext
from .git import get_current_edits, get_git_sha
from .shared import format_list

import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
import sys
import traceback


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


async def process_all_cases(id, cases, pipeline, max_concurrancy, completed):
    #
    # Generate static, pre-run metadata
    #
    start = datetime.now().timestamp()
    metadata = {
        "command": " ".join(sys.argv),
        "start": str(datetime.fromtimestamp(start, timezone.utc)),
        "concurrency": max_concurrancy,
    }
    result = {"results": {}, "metadata": metadata, "uuid": str(id)}

    try:
        sha = get_git_sha()
        edits = get_current_edits() if sha else None
        if sha:
            metadata["sha"] = sha
        if edits:
            metadata["edits"] = edits

        (config, stages) = pipeline.stages()
        metadata["pipeline"] = {"name": pipeline.name(), "config": config}

        #
        # Perform the run
        #
        semaphore = asyncio.Semaphore(max_concurrancy)

        async def sem_task(case):
            async with semaphore:
                return await process_one_case(case, stages, completed)

        tasks = [sem_task(case) for case in cases]
        results = await asyncio.gather(*tasks)

        #
        # Gather and record post-run metadata
        #
        end = datetime.now().timestamp()
        elapsed = end - start
        metadata["end"] = str(datetime.fromtimestamp(end, timezone.utc))
        metadata["elapsed"] = str(timedelta(seconds=elapsed))
        result["results"] = results

    except Exception as e:
        metadata["exception"] = {
            "message": str(e),
            "traceback": traceback.format_exc(),
            "time": str(datetime.now(timezone.utc)),
        }
    finally:
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
            raise ValueError(f"Model '{name}' not found. Available models include {names}.")
        return self._models[name]

    def register_pipeline(self, pipeline):
        name = pipeline.name()
        if name in self._pipelines:
            raise ValueError(f"Attempting to register duplicate pipeline '{name}'.")
        self._pipelines[name] = pipeline

    def pipeline(self, name):
        if name not in self._pipelines:
            names = format_list([k for k in self._pipelines.keys()])
            raise ValueError(f"Pipeline '{name}' not found. Available pipelines include {names}.")
        return self._pipelines[name]

    async def go(self, id, cases, pipeline, concurrency, progress, completed):
        # Run cases
        results = await process_all_cases(id, cases, pipeline, concurrency, completed)

        # Write log
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)
        output_file = os.path.join(log_folder, f"{results['uuid']}.json")
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        # TODO: This is a temporary fix to get around the fact that the progress bar doesn't
        # disappear when the task is completed. It just stops updating.
        if progress:
            progress.stop()

        return {"log": output_file, "results": results}


    # TODO: does summarize() really need to be in runner?
    def summarize(self, results):
        # TODO: checck that metadata.pipline exists
        # It probably exists because it is initialized in very early in
        # process_all_cases().
        pipeline_name = results["metadata"]["pipeline"]["name"]
        pipeline_config = results["metadata"]["pipeline"]["config"]
        pipeline_factory = self.pipeline(pipeline_name)
        pipeline = pipeline_factory(self, pipeline_config)
        pipeline.summarize(results)

    def format(self, results):
        # TODO: checck that metadata.pipline exists
        # It probably exists because it is initialized in very early in
        # process_all_cases().
        pipeline_name = results["metadata"]["pipeline"]["name"]
        pipeline_config = results["metadata"]["pipeline"]["config"]
        pipeline_factory = self.pipeline(pipeline_name)
        pipeline = pipeline_factory(self, pipeline_config)
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
        pipeline = pipeline_factory(self, pipeline_config)
        pipeline.compare(results_a, results_b)
