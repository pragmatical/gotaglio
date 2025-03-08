from abc import ABC, ABCMeta, abstractmethod
from copy import deepcopy


from .exceptions import ExceptionContext
from .shared import apply_patch, flatten_dict, merge_dicts, read_text_file

class EnsureSuperInitMeta(ABCMeta):
    """
    Metaclass to ensure that the base class's __init__ method is called in subclasses.
    This is useful for enforcing that subclasses properly initialize their base class.
    """
    def __init__(cls, name, bases, dct):
        original_init = cls.__init__

        def new_init(self, *args, **kwargs):
            # Call the original __init__ method
            original_init(self, *args, **kwargs)
            # Check if the base class __init__ was called
            if not hasattr(self, '_super_init_called'):
                raise RuntimeError(f"super().__init__() was not called in {name}.__init__")

        cls.__init__ = new_init
        super().__init__(name, bases, dct)

class Pipeline(ABC, metaclass=EnsureSuperInitMeta):
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

    def __init__(self, default_config, replacement_config, flat_config_patch):
        self._super_init_called = True
        super().__init__()
        base_config = replacement_config if replacement_config is not None else default_config
        self._config = apply_patch(base_config, flat_config_patch)
        ensure_required_configs(self._name, self._config)

    def config(self):
        return self._config
    
    @abstractmethod
    def stages(self):   
        pass

    @abstractmethod
    def compare(self, a, b):
        pass

    @abstractmethod
    def format(self, results, case_uuid_prefix):
        pass

    @abstractmethod
    def summarize(self, results):
        pass
    
class Prompt:
    def __init__(self, description):
        self._description = description

# TODO: can we deprecate and remove this?
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
            if isinstance(v, Prompt):
                raise ValueError(
                    f"{name} pipeline: missing '{k}' parameter. {v._description}"
                )
