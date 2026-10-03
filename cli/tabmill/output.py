"""Step markers: ✓ success / already-correct, ↷ soft-skip (yellow), ✗ operator action (red)."""

from rich.console import Console

console = Console(highlight=False)


def ok(msg: str) -> None:
    console.print(f"[green]✓[/green] {msg}")


def skip(msg: str) -> None:
    console.print(f"[yellow]↷[/yellow] {msg}")


def fail(msg: str) -> None:
    console.print(f"[red]✗[/red] {msg}")
