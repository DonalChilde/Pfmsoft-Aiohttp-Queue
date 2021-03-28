"""Console script entry point for pfmsoft_aiohttp_queue."""

import sys
from logging import Logger

import click

from pfmsoft_aiohttp_queue.app_config import LOGGER
from pfmsoft_aiohttp_queue.cli.example import hello

logger = LOGGER


@click.group()
@click.pass_context
def main(ctx: click.Context, args=None):
    """Console script for pfmsoft_aiohttp_queue."""
    # NOTE: as written, this code only runs when hello is called,
    # not when <entry point> --help is called. This is a group to
    # hold other commands and groups.
    ctx.obj = {}
    ctx.obj["important_value"] = {"key": "oh so important"}
    click.echo(
        "Replace this message by putting your code into "
        "pfmsoft_aiohttp_queue.cli.main"
    )
    click.echo(args)
    click.echo("See click documentation at https://click.palletsprojects.com/")
    logger.error("Just checking!")
    return 0


main.add_command(hello)
