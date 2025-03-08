from .shared import format_list


class Registry:
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

    # TODO: move these functions out of registry.
    def summarize(self, results):
        pipeline = self.create_pipeline(results)
        pipeline.summarize(results)

    def format(self, results, case_uuid_prefix):
        pipeline = self.create_pipeline(results)
        pipeline.format(results, case_uuid_prefix)

    def compare(self, results_a, results_b):
        pipeline = self.create_pipeline(results_a)
        pipeline.compare(results_a, results_b)

    def create_pipeline(self, results):
        pipeline_name = results["metadata"]["pipeline"]["name"]
        pipeline_config = results["metadata"]["pipeline"]["config"]
        pipeline_factory = self.pipeline(pipeline_name)
        pipeline = pipeline_factory(self, pipeline_config, {})
        return pipeline