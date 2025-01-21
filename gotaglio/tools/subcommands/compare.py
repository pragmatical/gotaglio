import os

from ..constants import log_folder
from ..shared import read_json_file, log_file_name_from_prefix


def compare(runner_factory, args):
    if not os.path.exists(log_folder):
        print(f"No log folder '{log_folder}'.")
        return

    prefix_a = args.prefix_a
    results_a = read_json_file(log_file_name_from_prefix(prefix_a))

    prefix_b = args.prefix_b
    results_b = read_json_file(log_file_name_from_prefix(prefix_b))

    runner = runner_factory()
    runner.compare(results_a, results_b)
