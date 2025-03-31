import os

from ..constants import app_configuration
from ..shared import log_file_name_from_prefix, read_json_file


def summarize(registry_factory, args):
    log_folder = app_configuration["log_folder"]
    if not os.path.exists(log_folder):
        print(f"No log folder '{log_folder}'.")
        return

    prefix = args.prefix
    results = read_json_file(log_file_name_from_prefix(prefix))

    registry = registry_factory()
    registry.summarize(results)
