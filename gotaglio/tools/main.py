from .constants import program_name
from .models import register_models
from .runner import Runner
from .subcommands.add_ids import add_ids
from .subcommands.compare import compare
from .subcommands.history import show_history
from .subcommands.models import list_models
from .subcommands.pipelines import list_pipelines
from .subcommands.rerun import rerun_pipeline
from .subcommands.run import run_pipeline
from .subcommands.summarize import summarize

import argparse


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
        prog=program_name, description="A tool for managing and running ML pipelines."
    )

    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # 'help' subcommand
    help_parser = subparsers.add_parser("help", help="Show help for gotaglio commands")
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

    # 'add-ids' subcommand
    add_ids_parser = subparsers.add_parser("add-ids", help="Add uuids to a suite")
    add_ids_parser.add_argument("suite", type=str, help="The name of a file with cases")
    add_ids_parser.add_argument(
        "--force", action="store_true", help="Force adding IDs even if they already exist"
    )

    # 'run' subcommand
    run_parser = subparsers.add_parser("run", help="Run a named pipeline")
    run_parser.add_argument("cases", type=str, help="The name of a file with cases")
    run_parser.add_argument(
        "pipeline", type=str, help="The name of the pipeline to run"
    )
    # key-value arguments are used to override the default pipeline configuration.
    run_parser.add_argument(
        "key_values", nargs="*", help="key=value arguments to configure pipeline"
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


    # Parse arguments
    args = parser.parse_args()

    # Route to the appropriate function based on the command
    try:
        if args.command == "help":
            show_help(parser, args.subcommand)

        elif args.command == "add-ids":
            add_ids(args.suite, args.force)

        elif args.command == "history":
            show_history()

        elif args.command == "models":
            list_models(runner_factory)

        elif args.command == "pipelines":
            list_pipelines(runner_factory)

        elif args.command == "run":
            config = parse_key_value_args(args.key_values)
            run_pipeline(runner_factory, args.cases, args.pipeline, config)

        elif args.command == "rerun":
            # config = parse_key_value_args(args.key_values)
            rerun_pipeline()
            # print("Rerun not yet implemented.")
            # run_pipeline(args.cases, args.pipeline, config)

        elif args.command == "summarize":
            summarize(runner_factory, args.prefix)

        elif args.command == "compare":
            compare(args.files)

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
