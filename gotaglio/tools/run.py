from .constants import log_folder

import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from git import Repo
import sys
import traceback
import uuid


async def process_one_case(case, pipeline):
    start = datetime.now().timestamp()
    result = {
        "succeeded": False,
        "metadata": {"start": str(datetime.fromtimestamp(start, timezone.utc))},
        "case": case,
        "stages": {},
    }
    for stage, func in pipeline.stages().items():
        try:
            result["stages"][stage] = await func(result)
        except Exception as e:
            result["exception"] = {
                "stage": stage,
                "message": str(e),
                "traceback": traceback.format_exc(),
                "time": str(datetime.now(timezone.utc)),
            }
            return result

    end = datetime.now().timestamp()
    elapsed = end - start
    result["metadata"]["end"] = str(datetime.fromtimestamp(end, timezone.utc))
    result["metadata"]["elapsed"] = str(timedelta(seconds=elapsed))
    result["succeeded"] = True
    return result


def get_git_sha(repo_path="."):
    try:
        repo = Repo(repo_path)
        sha = repo.head.commit.hexsha
        return sha
    except Exception as e:
        # print(f"Error: {e}")
        return None


def get_current_edits(repo_path="."):
    repo = Repo(repo_path)
    edits = {"modified": [], "added": [], "deleted": [], "untracked": [], "renamed": []}

    # Get modified, added, deleted, and renamed files
    for item in repo.index.diff(None):
        if item.change_type == "M":
            edits["modified"].append(item.a_path)
        elif item.change_type == "A":
            edits["added"].append(item.a_path)
        elif item.change_type == "D":
            edits["deleted"].append(item.a_path)
        elif item.change_type == "R":
            edits["renamed"].append(f"{item.a_path} -> {item.b_path}")

    # Get untracked files
    edits["untracked"] = repo.untracked_files

    return edits


async def process_all_cases(cases, pipeline, max_concurrancy):
    #
    # Generate static, pre-run metadata
    #
    id = uuid.uuid4()
    start = datetime.now().timestamp()
    metadata = {
        "command": " ".join(sys.argv),
        "start": str(datetime.fromtimestamp(start, timezone.utc)),
        "pipeline": pipeline.metadata(),
    }
    result = {"results": {}, "metadata": metadata, "uuid": str(id)}

    try:
        sha = get_git_sha()
        edits = get_current_edits() if sha else None
        if sha:
            metadata["sha"] = sha
        if edits:
            metadata["edits"] = edits

        #
        # Perform the run
        #
        semaphore = asyncio.Semaphore(max_concurrancy)

        async def sem_task(case):
            async with semaphore:
                return await process_one_case(case, pipeline)

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

def format_list(values):
    if not values:
        return ""
    elif len(values) == 1:
        return values[0]
    elif len(values) == 2:
        return f"{values[0]} and {values[1]}"
    else:
        return f"{', '.join(values[:-1])}, and {values[-1]}"


class Runner:
    _models = {}
    _pipelines = {}

    def __init__(self):
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

    def register_pipeline(self, name, pipeline):
        if name in self._pipelines:
            raise ValueError(f"Attempting to register duplicate pipeline '{name}'.")
        self._pipelines[name] = pipeline

    def pipeline(self, name):
        if name not in self._pipelines:
            names = format_list([k for k in self._pipelines.keys()])
            raise ValueError(f"Pipeline '{name}' not found. Available pipelines include {names}.")
        return self._pipelines[name]

    async def go(self, cases, pipeline_name, pipeline_config):
        pipeline_factory = self.pipeline(pipeline_name)
        pipeline = pipeline_factory(self, pipeline_config)
        results = await process_all_cases(cases, pipeline, 2)

        if not os.path.exists(log_folder):
            os.makedirs(log_folder)
        output_file = os.path.join(log_folder, f"{results['uuid']}.json")
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print(json.dumps(results, indent=2))
        pipeline.summarize(results)

        return {"log": output_file, "results": results}

    def summarize(self, results):
        pipeline_name = results["metadata"]["pipeline"]["name"]
        pipeline_config = results["metadata"]["pipeline"]["config"]
        pipeline_factory = self.pipeline(pipeline_name)
        pipeline = pipeline_factory(self, pipeline_config)
        pipeline.summarize(results)
