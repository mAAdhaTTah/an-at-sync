import json
from pathlib import Path
from typer import Option, Typer

from an_at_sync.program import Program, ProgramSettings

main = Typer()

ConfigOption = Option(
    "config.py",
    help="Config file to load",
    exists=True,
    file_okay=True,
    dir_okay=False,
    resolve_path=True,
)


@main.command("sync")
def sync(config: Path = ConfigOption):
    config_file = Program.load_config(config)

    program = Program(
        settings=ProgramSettings(),
        activist_class=config_file.Activist,
        event_class=config_file.Event,
        rsvp_class=config_file.RSVP,
    )

    for sync_result in program.sync_events():
        program.write_result(sync_result)


@main.command("webhook")
def webhook(
    config: Path = ConfigOption,
    webhook: Path = Option(
        ...,
        help="JSON file containing webhook body",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
):
    config_file = Program.load_config(config)

    program = Program(
        settings=ProgramSettings(),
        activist_class=config_file.Activist,
        event_class=config_file.Event,
        rsvp_class=config_file.RSVP,
    )
    with open(webhook) as f:
        webhook_body = json.load(f)

    for result in program.handle_webhook(webhook_body):
        program.write_result(result)
