"""hermes-pocket plugin entry point."""
from __future__ import annotations


def register(ctx) -> None:
    """Called by the Hermes plugin loader."""
    from .pocket import cli as pocket_cli

    pocket_cli.register(ctx)
