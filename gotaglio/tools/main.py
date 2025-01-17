from .constants import log_folder, model_config_file
from .models import register_models
from .pipelines import register_pipelines
from .run import Runner

import argparse
import asyncio
import json
import os


def parse_key_value_args(args):
    """Parse key=value arguments into a dictionary."""
    config = {}
    for arg in args:
        if "=" not in arg:
            raise argparse.ArgumentTypeError(
                f"Invalid format: '{arg}'. Expected key=value."
            )
        key, value = arg.split("=", 1)
        config[key] = value
    return config


def main(pipelines):
    # Use runner_factory to hold Runner configuration until we
    # actually need to instantiate a Runner. This avoids Runner
    # instantiation exceptions before argument parsing exceptions.
    def runner_factory():
        runner = Runner()
        for (key, value) in pipelines.items():
            runner.register_pipeline(key, value)
        register_models(runner)
        return runner

    #
    # Configure command line parsing.
    #
    parser = argparse.ArgumentParser(
        prog="gotag", description="A tool for managing and running ML pipelines."
    )

    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # 'help' subcommand
    help_parser = subparsers.add_parser("help", help="Show help for gotag")
    help_parser.add_argument(
        "subcommand", nargs="?", help="The subcommand to show help for"
    )

    # 'history' subcommand
    history_parser = subparsers.add_parser(
        "history", help="Show information about recent runs"
    )

    # 'models' subcommand
    models_parser = subparsers.add_parser("models", help="List available models")

    # 'pipelines' subcommand
    pipelines_parser = subparsers.add_parser(
        "pipelines", help="List available pipelines"
    )

    # 'run' subcommand
    rerun_parser = subparsers.add_parser(
        "rerun", help="Rerun an experiment with modifications."
    )
    rerun_parser.add_argument(
        "key_values", nargs="*", help="key=value arguments to configure pipeline"
    )

    # 'run' subcommand
    run_parser = subparsers.add_parser("run", help="Run a named pipeline")
    run_parser.add_argument("cases", type=str, help="The name of a file with cases")
    run_parser.add_argument(
        "pipeline", type=str, help="The name of the pipeline to run"
    )

    # 'summarize' subcommand
    summarize_parser = subparsers.add_parser("summarize", help="Summarize a run")
    summarize_parser.add_argument(
        "prefix", type=str, help="Filename prefix for run log"
    )

    # 'compare' subcommand
    compare_parser = subparsers.add_parser(
        "compare", help="Compare two or more label sets"
    )
    compare_parser.add_argument("files", nargs="+", help="Label set files to compare")

    # key-value arguments are used to override the default pipeline configuration.
    run_parser.add_argument(
        "key_values", nargs="*", help="key=value arguments to configure pipeline"
    )

    # Parse arguments
    args = parser.parse_args()

    # Route to the appropriate function based on the command
    try:
        if args.command == "help":
            show_help(parser, args.subcommand)

        elif args.command == "models":
            list_models(runner_factory)

        elif args.command == "pipelines":
            list_pipelines(runner_factory)

        elif args.command == "run":
            config = parse_key_value_args(args.key_values)
            run_pipeline(runner_factory, args.cases, args.pipeline, config)

        elif args.command == "rerun":
            print("Rerun not yet implemented.")
            # config = parse_key_value_args(args.key_values)
            # run_pipeline(args.cases, args.pipeline, config)

        elif args.command == "summarize":
            summarize(runner_factory, args.prefix)

        elif args.command == "compare":
            compare_labels(args.files)

        else:
            parser.print_help()
    except ValueError as e:
        print(f"Error: {e}")


def show_help(parser, subcommand):
    if subcommand:
        subcommand_parser = next(
            (
                p
                for p in parser._subparsers._actions[1].choices.values()
                if p.prog.endswith(subcommand)
            ),
            None,
        )
        if subcommand_parser:
            subcommand_parser.print_help()
        else:
            print(f"No help available for subcommand: {subcommand}")
    else:
        parser.print_help()


def list_models(runner_factory):
    runner = runner_factory()
    print("Available models:")
    for model in runner._models:
        print(model)


def list_pipelines(runner_factory):
    runner = runner_factory()
    print("Available pipelines:")
    for pipeline in runner._pipelines:
        print(pipeline)


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


def summarize(runner_factory, prefix):
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
    register_models(runner, model_config_file)
    register_pipelines(runner)
    runner.summarize(results)


def compare_labels(files):
    print(f"Comparing label sets from files: {', '.join(files)}")


def get_filenames_with_prefix(folder_path, prefix):
    """
    Returns a list of filenames in the specified folder that start with the given prefix.

    :param folder_path: Path to the folder to search.
    :param prefix: The prefix to filter filenames.
    :return: List of filenames that start with the prefix.
    """
    try:
        # List all files in the folder
        filenames = [
            filename
            for filename in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, filename))
            and filename.startswith(prefix)
        ]
        return filenames
    except FileNotFoundError:
        print(f"Error: Folder '{folder_path}' not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []
