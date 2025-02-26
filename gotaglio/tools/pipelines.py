from abc import ABC, abstractmethod
from copy import deepcopy
from glom import assign, glom


from .exceptions import ExceptionContext
from .shared import flatten_dict, merge_dicts, read_text_file
from .templating import jinja2_template

class Pipeline(ABC):
    """
    Abstract base class for pipelines.

    Attributes:
        _name (str): The name of the pipeline. Must be defined in subclasses.
        _description (str): A brief description of the pipeline. Must be defined in subclasses.

    Methods:
        name(cls):
            Returns the name of the pipeline.
        
        stages(self):
            Abstract method that returns a dict of named stages in the pipeline.
            Each stage is a function that takes a single, `results` object parameter.
            Stages are run in the order they appear in the dict.
        
        compare(self, a, b):
            Abstract method that compares results from two pipeline runs.
            No return value. Should either print a summary or write it to a file.
        
        format(self, results):
            Abstract method that should format the results of a pipeline run.
            No return value. Should either print a summary or write it to a file.
        
        summarize(self, results):
            Abstract method that should summarize the results of a pipeline run.
            No return value. Should either print a summary or write it to a file.

    Raises:
        NotImplementedError: If the subclass does not define _name or _description attributes.
    """
    _name = None
    _description = None

    @classmethod
    def name(cls):
        return cls._name

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls._name is None:
            raise NotImplementedError(f"Class {cls.__name__} must define a static _name attribute")
        if cls._description is None:
            raise NotImplementedError(f"Class {cls.__name__} must define a static _description attribute")

    @abstractmethod
    def stages(self):   
        pass

    @abstractmethod
    def compare(self, a, b):
        pass

    @abstractmethod
    def format(self, results):
        pass

    @abstractmethod
    def summarize(self, results):
        pass
    

def merge_configs(base_config, patch_config, replace_config=False):
    if replace_config:
        return deepcopy(patch_config)
    else:
        return merge_dicts(base_config, patch_config)


def ensure_required_configs(name, config):
    """
    Raises a ValueError if any required configuration setting is missing.

    Args:
        name (str): The name of the pipeline.
        config (dict): The configuration dictionary to validate.

    Raises:
        ValueError: If any setting in the configuration is `None`.
    """
    settings = flatten_dict(config)
    with ExceptionContext(
        f"Pipeline '{name}' checking settings."
    ):
        for k, v in settings.items():
            if v is None:
                raise ValueError(
                    f"{name} pipeline: missing '{k}' parameter."
                )


def build_template(config, template_file, template_source_text):
    # If we don't have the template source text, load it from a file.
    if not isinstance(
        glom(config, template_source_text, default=None),
        str,
    ):
        assign(
            config,
            template_source_text,
            read_text_file(glom(config, template_file)),
        )

    # Compile the template.
    return jinja2_template(
        glom(config, "prepare.template_text")
    )

