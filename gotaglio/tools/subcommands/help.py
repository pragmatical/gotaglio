def show_help(parser, args):
    subcommand = args.subcommand
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
