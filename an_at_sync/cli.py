from typer import Option, Typer

from an_at_sync.program import Program, ProgramSettings

main = Typer()


@main.command()
def run(
    config: str = Option("config.py", help="Config file to load"),
):
    config_file = Program.load_config(config)

    program = Program(
        settings=ProgramSettings(
            an_api_key=config_file.AN_API_KEY,
            at_base=config_file.AT_BASE,
            at_activists_table=config_file.AT_ACTIVISTS_TABLE,
            at_events_table=config_file.AT_EVENTS_TABLE,
            at_rsvp_table=config_file.AT_RSVP_TABLE,
            at_api_key=config_file.AT_API_KEY,
        ),
        activist_class=config_file.Activist,
        event_class=config_file.Event,
        rsvp_class=config_file.RSVP,
    )

    for sync_result in program.sync_events():
        program.write_result(sync_result)
