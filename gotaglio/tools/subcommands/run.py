import asyncio
import json

def run_pipeline(runner_factory, cases_file, pipeline, config):
    runner = runner_factory()
    try:
        with open(cases_file, "r") as file:
            cases = json.load(file)
    except FileNotFoundError:
        raise ValueError(f"File {cases_file} not found.")
    except json.JSONDecodeError:
        raise ValueError(f"Error decoding JSON from file {cases_file}.")

    x = asyncio.run(runner.go(cases, pipeline, config))
    print(f'Results written to {x["log"]}')
