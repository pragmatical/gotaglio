import asyncio
import uuid

# WARNING: don't use the `from gotaglio.constants import log_foler`
# as if will import a copy of log_folder. We need a reference because
# it can be overwritten and all users must see the same value.
import gotaglio.constants

from .director import Director
from .models import register_models
from .registry import Registry
from .shared import read_json_file, read_log_file_from_prefix


class Gotaglio:
    """
    Gotaglio is a class that provides methods to manage and manipulate tags.
    """

    def __init__(self, log_folder_param, pipelines):
        # Set the global log folder that is defined in constants.py.
        gotaglio.constants.log_folder = log_folder_param

        def create_registry():
            registry = Registry()
            for pipeline in pipelines:
                registry.register_pipeline(pipeline)
            register_models(registry)
            return registry

        self._registry_factory = create_registry

    # def register_model(self, model):
    #     pass

    # def register_pipeline(self, pipeline):
    #     pass

    def add_ids(self, cases, force=False):
        # TODO: allow either a runlog object or a string id prefix
        add_count = 0
        for case in cases:
            if "uuid" not in case or force:
                case["uuid"] = str(uuid.uuid4())
                add_count += 1
        print(f"Total cases: {len(cases)}")
        print(f"UUIDs added: {add_count}")

    def compare(self, a, b):
        runlog_a = runlog_from_runlog_or_prefix(a)
        runlog_b = runlog_from_runlog_or_prefix(b)
        registry = self._registry_factory()
        registry.compare(runlog_a, runlog_b)

    def format(self, runlog_or_prefix, case_uuid_prefix=None):
        runlog = runlog_from_runlog_or_prefix(runlog_or_prefix)
        registry = self._registry_factory()
        x = registry.format(runlog, case_uuid_prefix)
        return x

    def load(self, uuid_prefix):
        return read_log_file_from_prefix(uuid_prefix)

    def rerun(self, runlog_or_prefix, flat_config_patch={}, concurrency=2, save=False):
        runlog = runlog_from_runlog_or_prefix(runlog_or_prefix)
        cases = [record["case"] for record in runlog["results"]]
        metadata = runlog["metadata"]
        if "pipeline" not in metadata:
            raise Exception("No pipeline metadata found in results file")

        pipeline_name = metadata["pipeline"]["name"]
        replacement_config = metadata["pipeline"]["config"]

        director = Director(
            self._registry_factory,
            pipeline_name,
            cases,
            replacement_config,
            flat_config_patch,
            concurrency,
        )

        asyncio.run(director.process_all_cases(ProgressMock(), completed_mock))
        director.summarize_results()

        if save:
            director.write_results()

        return director._results

    def run(
        self,
        pipeline_name,
        cases_or_filename,
        flat_config_patch={},
        concurrency=2,
        save=False,
    ):
        cases = cases_from_cases_or_filename(cases_or_filename)
        director = Director(
            self._registry_factory,
            pipeline_name,
            cases,
            None,
            flat_config_patch,
            concurrency,
        )

        asyncio.run(director.process_all_cases(ProgressMock(), completed_mock))
        director.summarize_results()

        if save:
            director.write_results()

        return director._results

    def save(self, runlog, filename=None):
        pass

    def summarize(self, runlog_or_prefix):
        runlog = runlog_from_runlog_or_prefix(runlog_or_prefix)
        registry = self._registry_factory()
        registry.summarize(runlog)


def runlog_from_runlog_or_prefix(runlog_or_prefix):
    if isinstance(runlog_or_prefix, str):
        return read_log_file_from_prefix(runlog_or_prefix)
    return runlog_or_prefix


def cases_from_cases_or_filename(cases_or_filename):
    if isinstance(cases_or_filename, str):
        return read_json_file(cases_or_filename)
    return cases_or_filename


class ProgressMock:
    def stop(self):
        pass


def completed_mock():
    pass


def is_running_in_notebook():
    try:
        from IPython import get_ipython

        if "IPKernelApp" in get_ipython().config:
            return True
    except ImportError:
        return False
    return False
