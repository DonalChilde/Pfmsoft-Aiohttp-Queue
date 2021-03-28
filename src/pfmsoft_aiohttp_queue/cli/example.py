"""An example of a click command."""
import click


@click.command()
@click.argument("name")
@click.pass_context
def hello(ctx: click.Context, name):
    """Make a polite greeting"""
    click.echo(f"Hello {name}!")
    click.echo(f"here is an important value! {ctx.obj['important_value']}")
