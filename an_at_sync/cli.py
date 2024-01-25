import json
from pathlib import Path

from typer import Argument, Option, Typer

from an_at_sync.model import BaseEvent
from an_at_sync.program import Program, ProgramSettings

main = Typer()


@main.command("init")
def init():
    pass


sync = Typer()
main.add_typer(sync, name="sync")


@sync.command("events")
def events(sync_rsvps: bool = Option(False, "--rsvps")):
    program = Program(
        settings=ProgramSettings(),
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
    )
):
    with webhook_path.open() as f:
        body = json.load(f)

    program = Program(
        settings=ProgramSettings(),
    )
    program.handle_webhook(body)
