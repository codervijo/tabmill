"""Step markers: ✓ success / already-correct, ↷ soft-skip (yellow), ✗ operator action (red).
Messages are plain text: `[...]` in them (AI output, rule messages) is escaped, not markup."""

from rich.console import Console
from rich.markup import escape

console = Console(highlight=False)


def ok(msg: str) -> None:
    console.print(f"[green]✓[/green] {escape(msg)}")


def skip(msg: str) -> None:
    console.print(f"[yellow]↷[/yellow] {escape(msg)}")


def fail(msg: str) -> None:
    console.print(f"[red]✗[/red] {escape(msg)}")
