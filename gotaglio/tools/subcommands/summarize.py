import os

from ..constants import log_folder
from ..shared import get_filenames_with_prefix, log_file_name_from_prefix, read_json_file


def summarize(runner_factory, args):
    if not os.path.exists(log_folder):
        print(f"No log folder '{log_folder}'.")
        return

    prefix = args.prefix
    results = read_json_file(log_file_name_from_prefix(prefix))

    runner = runner_factory()
    runner.summarize(results)
