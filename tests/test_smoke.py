"""Smoke tests to verify project setup."""


def test_import() -> None:
    """Verify the package can be imported."""
    from dotclaude import __version__

    assert __version__ == "0.4.0"


def test_cli_import() -> None:
    """Verify typer app can be imported."""
    from dotclaude.cli import app

    assert app is not None
