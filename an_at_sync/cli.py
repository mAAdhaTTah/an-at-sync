import json
from pathlib import Path

from typer import Argument, Option, Typer

from an_at_sync.model import BaseEvent
from an_at_sync.program import Program, ProgramSettings


class Pipedream:
    def __init__(self, steps: dict) -> None:
        self.steps = steps


main = Typer()

ConfigOption = Option(
    "config.py",
    help="Config file to load",
    exists=True,
    file_okay=True,
    dir_okay=False,
    resolve_path=True,
)


@main.command("init")
def init():
    pass


sync = Typer()
main.add_typer(sync, name="sync")


@sync.command("events")
def events(config: Path = ConfigOption, sync_rsvps: bool = Option(False, "--rsvps")):
    config_file = Program.load_config(config)

    program = Program(
        settings=ProgramSettings(),
        activist_class=config_file.Activist,
        event_class=config_file.Event,
        rsvp_class=config_file.RSVP,
    )

    for event_result in program.sync_events():
        program.write_result(event_result)

        if (
            sync_rsvps
            and event_result.status != "failed"
            and isinstance(event_result.instance, BaseEvent)
        ):
            for rsvp_result in program.sync_rsvps_from_event(event_result.instance):
                program.write_result(rsvp_result)


@main.command("webhook")
def webhook(
    webhook_path: Path = Argument(
        ...,
        help="JSON file containing webhook body",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    config: Path = ConfigOption,
):
    config_file = Program.load_config(config)

    with open(webhook_path) as f:
        trigger = json.load(f)

    pd = Pipedream(steps={"trigger": trigger})
    config_file.handler(pd)
