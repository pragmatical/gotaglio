import asyncio
import uuid

from .director import Director
from .models import register_models
from .registry import Registry


class Gotaglio:
    """
    Gotaglio is a class that provides methods to manage and manipulate tags.
    """

    def __init__(self, pipelines=[]):
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

    def compare(self, runlog_a, runlog_b):
        # TODO: allow either a runlog object or a string id prefix
        registry = self._registry_factory()
        registry.compare(runlog_a, runlog_b)

    def format(self, runlog, case_uuid_prefix=None):
        # TODO: allow either a runlog object or a string id prefix
        registry = self._registry_factory()
        registry.format(runlog, case_uuid_prefix)

    def load(self, uuid_prefix):
        pass

    def rerun(self, runlog, flat_config_patch={}, concurrency=2):
        # TODO: allow either a runlog object or a string id prefix
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
        return director._results

    def run(self, pipeline_name, cases, flat_config_patch={}, concurrency=2):
        # TODO: allow either a cases object or a string filename
        director = Director(
            self._registry_factory,
            pipeline_name,
            cases,
            None,
            flat_config_patch,
            concurrency,
        )

        asyncio.run(director.process_all_cases(ProgressMock(), completed_mock))
        return director._results

    def save(self, cases):
        pass

    def summarize(self, runlog):
        registry = self._registry_factory()
        registry.summarize(runlog)


class ProgressMock:
    def stop(self):
        pass


def completed_mock():
    pass
