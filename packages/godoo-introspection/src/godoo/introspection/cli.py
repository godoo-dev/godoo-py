"""CLI entrypoint for godoo-introspection: godoo-introspect command."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

if TYPE_CHECKING:
    from godoo.client.client import OdooClient

logger = logging.getLogger("godoo_introspection.cli")

# ------------------------------------------------------------------
# App setup
# ------------------------------------------------------------------

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)


@app.callback()
def _callback() -> None:
    """Odoo schema introspection tools."""


# ------------------------------------------------------------------
# generate command
# ------------------------------------------------------------------


@app.command()
def generate(
    output: Annotated[str, typer.Option(help="Output directory for generated model files")],
    models: Annotated[
        str | None, typer.Option(help="Comma-separated fnmatch patterns, e.g. 'project.*,res.partner'")
    ] = None,
    all: Annotated[bool, typer.Option("--all", help="Generate all installed models")] = False,
    url: Annotated[str | None, typer.Option(envvar="ODOO_URL", help="Odoo URL")] = None,
    db: Annotated[str | None, typer.Option(envvar="ODOO_DB", help="Odoo database name")] = None,
    user: Annotated[str | None, typer.Option(envvar="ODOO_USER", help="Odoo username")] = None,
    password: Annotated[str | None, typer.Option(envvar="ODOO_PASSWORD", hide_input=True, help="Odoo password")] = None,
) -> None:
    """Generate Pydantic model files from a live Odoo instance schema."""
    # -- Validation: mutual exclusion --
    if models and all:
        typer.echo("Error: --models and --all are mutually exclusive.", err=True)
        raise typer.Exit(code=1)

    # -- Validation: at least one selection flag required --
    if not models and not all:
        typer.echo("Error: provide --models <patterns> or --all to select models.", err=True)
        raise typer.Exit(code=1)

    # -- Validation: output directory must exist --
    output_path = Path(output)
    if not output_path.is_dir():
        typer.echo(f"Error: output directory {output!r} does not exist.", err=True)
        raise typer.Exit(code=1)

    # -- Credential assembly --
    from godoo.client.client import OdooClientConfig  # deferred import
    from godoo.client.config import config_from_env  # deferred import
    from godoo.client.errors import OdooError  # deferred import

    # If all four credentials are supplied as explicit flags, use them directly —
    # no need to call config_from_env() (which would require env vars to be set).
    if url is not None and db is not None and user is not None and password is not None:
        config = OdooClientConfig(url=url, database=db, username=user, password=password)
    else:
        # Fall back to env vars, then override any explicitly-provided flag values
        try:
            config = config_from_env()
        except OdooError as exc:
            # Echo the error message — it names missing variable names, not values (safe per T-07-07)
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(code=1) from exc

        # Override with any explicit flag values
        if url is not None or db is not None or user is not None or password is not None:
            config = OdooClientConfig(
                url=url if url is not None else config.url,
                database=db if db is not None else config.database,
                username=user if user is not None else config.username,
                password=password if password is not None else config.password,
            )

    # -- Async execution bridge --
    # Finding #6: catch OdooError (auth, network) in addition to ValueError so
    # auth failures and connection errors produce a clean stderr message + exit 1
    # instead of a raw traceback. str(exc) for OdooError never includes the password
    # (the message is "invalid login" etc.) — safe per T-w2x-02.
    try:
        asyncio.run(_generate_async(output_path, models, all, config))
    except (ValueError, OdooError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


# ------------------------------------------------------------------
# Async core
# ------------------------------------------------------------------


async def _generate_async(
    output_dir: Path,
    models_arg: str | None,
    all_arg: bool,
    config: object,
) -> None:
    """Async implementation of the generate command."""
    import fnmatch  # stdlib

    from godoo.client.client import OdooClient  # deferred runtime import
    from godoo.introspection.codegen import CodeGenerator
    from godoo.introspection.introspector import Introspector

    client: OdooClient = OdooClient(config)  # type: ignore[arg-type]
    try:
        await client.authenticate()

        # Fetch all installed non-transient model names
        ir_model_records = await client.search_read(
            "ir.model",
            [("transient", "=", False)],
            fields=["model"],
        )
        all_names: list[str] = [r["model"] for r in ir_model_records]

        # Apply selection filter
        if models_arg:
            patterns = [p.strip() for p in models_arg.split(",") if p.strip()]
            selected = [n for n in all_names if any(fnmatch.fnmatch(n, p) for p in patterns)]
        else:
            selected = all_names

        # Zero matches — raise so the sync wrapper can surface it cleanly
        if not selected:
            raise ValueError("No models matched the given patterns.")

        # Introspect and generate
        introspector = Introspector(client)
        schemas = await introspector.get_schemas(selected)
        in_set = frozenset(schemas.keys())
        generator = CodeGenerator(introspector, in_set=in_set)
        generator.write(list(schemas.values()), output_dir)

        typer.echo(f"Generated {len(schemas)} model(s) to {output_dir}")
        logger.info("Generated %d model(s) to %s", len(schemas), output_dir)
    finally:
        await client.aclose()
