"""Serve command — prints instructions for starting the dotclaude server."""

from __future__ import annotations

import typer
from rich.console import Console

_console = Console()
serve_app = typer.Typer(name="serve", help="Show instructions for starting the dotclaude web server")


@serve_app.callback(invoke_without_command=True)
def serve() -> None:
    """Show instructions for starting the dotclaude web server."""
    _console.print("""
[bold]dotclaude web server[/bold]

The server is maintained in a separate repository:
  [cyan]https://github.com/jeonghwan-hwang/dotclaude-server[/cyan]

[bold]Quick start:[/bold]

  [dim]# 1. Clone the server repository[/dim]
  git clone https://github.com/jeonghwan-hwang/dotclaude-server.git
  cd dotclaude-server

  [dim]# 2. Start PostgreSQL[/dim]
  docker-compose up -d

  [dim]# 3. Install Python dependencies[/dim]
  pip install -e ".[dev]"

  [dim]# 4. Configure environment[/dim]
  cp env.example .env
  [dim]# Edit .env -- set JWT_SECRET, JWT_REFRESH_SECRET[/dim]

  [dim]# 5. Run database migrations[/dim]
  alembic upgrade head

  [dim]# 6. Start the server[/dim]
  uvicorn app.main:app --reload --port 3000

  [dim]# 7. Sync your data[/dim]
  dotclaude register
  dotclaude sync

  [dim]# 8. Open browser[/dim]
  open http://localhost:3000

[bold]Docker:[/bold]

  cd dotclaude-server
  docker build -t dotclaude-server .
  docker run -p 3000:3000 --env-file .env dotclaude-server
""")
