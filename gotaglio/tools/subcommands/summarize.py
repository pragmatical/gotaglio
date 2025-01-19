from ..constants import log_folder
from ..shared import get_filenames_with_prefix

import json
import os

def summarize(runner_factory, args):
    prefix = args.prefix
    filenames = get_filenames_with_prefix(log_folder, prefix)
    if not filenames:
        print(f"No files found with prefix '{prefix}'.")
        return
    if len(filenames) > 1:
        print(f"Multiple files found with prefix '{prefix}':")
        for filename in filenames:
            print(filename)
        return

    with open(os.path.join(log_folder, filenames[0]), "r") as file:
        results = json.load(file)
    runner = runner_factory()
    runner.summarize(results)
