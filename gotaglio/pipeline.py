from datetime import datetime, timedelta, timezone
import traceback
from typing import Any

from .dag import run_dag

from .exceptions import ExceptionContext
from .mocks import Flakey, Perfect
from .registry import Registry
from .shared import apply_patch, flatten_dict
from .pipeline_spec import PipelineSpec


class Pipeline:
    def __init__(
        self,
        spec: PipelineSpec,
        replacement_config: dict[str, Any] | None,
        flat_config_patch: dict[str, Any],
        global_registry: Registry,
    ):
        self._spec = spec

        # Merge and validate configurations.
        self._config = apply_patch(
            (
                replacement_config
                if replacement_config is not None
                else spec.configuration
            ),
            flat_config_patch,
        )
        ensure_required_configs(spec.name, spec.configuration, self._config)

        # Construct and register some model mocks, specific to this pipeline.
        # NOTE: this must be done before spec.create_dag, which accesses
        # models from the registry.
        registry = Registry(global_registry)
        Flakey(registry, spec.expected, {})
        Perfect(registry, spec.expected, {})

        # Create the DAG.
        turn_dag = spec.create_dag(spec.name, self._config, registry)
        self._dag = turn_dag

    def get_config(self):
        return self._config

    def get_dag(self):
        return self._dag

    def diff_configs(self):
        return diff_configs(self._spec.configuration, self._config)


def diff_configs(default_config: dict[str, Any], config: dict[str, Any]):
    default_config = flatten_dict(default_config)
    config = flatten_dict(config)
    diff = []
    for k, v in config.items():
        if k not in default_config:
            diff.append((k, None, config[k]))
        elif default_config[k] != v and not isinstance(default_config[k], Internal):
            diff.append((k, format_config(default_config[k]), v))
    for k, v in default_config.items():
        if k not in config and not isinstance(v, Internal):
            diff.append((k, format_config(default_config[k]), None))
    return diff


def format_config(x):
    if isinstance(x, Prompt):
        return "PROMPT"
    else:
        return x


# Value in Pipeline configuration, indicating the value should be supplied by
# key=value pairs on the command line.
class Prompt:
    def __init__(self, description):
        self._description = description


# Value in Pipeline configuration, indicating the value will be supplied by the
# Pipeline runtime. Using a value of Internal will prevent the corresponding
# key from being displayed in help messages.
class Internal:
    def __init__(self):
        pass


def ensure_required_configs(name, default_config, config):
    """
    Raises a ValueError if any required configuration setting is missing.

    Args:
        name (str): The name of the pipeline.
        config (dict): The configuration dictionary to validate.

    Raises:
        ValueError: If any setting in the configuration is `None`.
    """
    settings = flatten_dict(config)
    with ExceptionContext(f"Pipeline '{name}' checking settings."):
        for k, v in settings.items():
            if isinstance(v, Prompt):
                lines = [
                    f"{name} pipeline: missing '{k}' parameter.",
                    "",
                    "Required settings:",
                ]
                prompts = [
                    (k, v)
                    for k, v in flatten_dict(default_config).items()
                    if isinstance(v, Prompt)
                ]
                lines.extend([f"  {k}: {v._description}" for k, v in prompts])
                raise ValueError("\n".join(lines))


async def process_one_case(case, dag, completed):
    ExceptionContext.clear_context()
    start = datetime.now().timestamp()
    result = {
        "succeeded": False,
        "metadata": {"start": str(datetime.fromtimestamp(start, timezone.utc))},
        "case": case,
    }

    try:
        await run_dag(dag, result)
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
