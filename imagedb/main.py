from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path
from typing import Optional

import typer
from PIL import Image
from rich import print, box
from rich.table import Table
from rich.prompt import Prompt

from .clipboard import ClipboardError, copy_image_to_clipboard, read_image_from_clipboard
from .config import DEFAULT_VISION_MODEL, load_config, save_config
from .database import ImageDB
from .openrouter import describe_image, get_embedding

app = typer.Typer(add_completion=False, help="Image database CLI.")


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _save_png_bytes(image_bytes: bytes, destination: Path) -> None:
    destination.write_bytes(image_bytes)


def _require_config():
    try:
        return load_config()
    except (FileNotFoundError, ValueError) as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc


@app.command("init")
def init_command():
    """
    Interactive setup wizard.
    """
    api_key = typer.prompt("Enter your OpenRouter API key", hide_input=True)
    vision_model = typer.prompt(
        "Vision model to use",
        default=DEFAULT_VISION_MODEL,
    )
    path = save_config(api_key=api_key, vision_model=vision_model)
    print(f"[green]Config saved to {path}[/green]")


@app.command("config")
def config_command(
    api_key: Optional[str] = typer.Option(None, help="Set a new API key."),
    vision_model: Optional[str] = typer.Option(None, help="Set a new vision model."),
    show: bool = typer.Option(
        False, "--show", help="Show current configuration instead of modifying."
    ),
):
    """
    View or modify settings.
    """
    cfg = _require_config()

    if show or (api_key is None and vision_model is None):
        print(cfg)
        raise typer.Exit()

    if api_key:
        cfg["api_key"] = api_key
    if vision_model:
        cfg["vision_model"] = vision_model

    path = save_config(api_key=cfg["api_key"], vision_model=cfg.get("vision_model"))
    print(f"[green]Updated config at {path}[/green]")


@app.command("save")
def save_command(
    context: Optional[str] = typer.Argument(
        None,
        help="Optional extra context to guide the description (e.g., names, places).",
    )
):
    """
    Copy image from clipboard into the DB (describe + embed).
    """
    cfg = _require_config()
    api_key = cfg["api_key"]
    vision_model = cfg.get("vision_model", DEFAULT_VISION_MODEL)

    try:
        image_bytes = read_image_from_clipboard()
    except ClipboardError as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    file_hash = _hash_bytes(image_bytes)

    db = ImageDB()
    image_path = db.image_dir / f"{file_hash}.png"

    if image_path.exists():
        print(f"[yellow]Image already saved at {image_path}[/yellow]")
    else:
        _save_png_bytes(image_bytes, image_path)
        print(f"[green]Saved image to {image_path}[/green]")

    description = describe_image(
        image_bytes, api_key=api_key, model=vision_model, context=context
    )
    print(f"[cyan]Description:[/cyan] {description}")

    embedding = get_embedding(description, api_key=api_key)
    db.add_image(
        embedding=embedding,
        description=description,
        file_hash=file_hash,
        original_filename="clipboard.png",
    )
    print("[green]Stored metadata and embedding in the database.[/green]")


@app.command("load")
def load_command(query: str):
    """
    Search by text and copy the best match to the clipboard.
    """
    cfg = _require_config()
    api_key = cfg["api_key"]

    embedding = get_embedding(query, api_key=api_key)
    db = ImageDB()
    results = db.search(embedding, limit=1)
    if not results:
        print("[yellow]No results found.[/yellow]")
        raise typer.Exit()

    result = results[0]
    path_value = result.get("path") if isinstance(result, dict) else getattr(result, "path", None)
    if not path_value:
        print("[red]Result missing file path.[/red]")
        raise typer.Exit(code=1)

    path = Path(path_value)
    if not path.exists():
        print(f"[red]Image file missing at {path}[/red]")
        raise typer.Exit(code=1)

    copy_image_to_clipboard(path)
    print(f"[green]Copied image to clipboard from {path}[/green]")


@app.command("search")
def search_command(query: str):
    """
    Search by text and show top 5 matches with metadata.
    """
    cfg = _require_config()
    api_key = cfg["api_key"]

    embedding = get_embedding(query, api_key=api_key)
    db = ImageDB()
    results = db.search(embedding, limit=5)

    if not results:
        print("[yellow]No results found.[/yellow]")
        raise typer.Exit()

    table = Table(title=f"Search Results for '{query}'", box=box.ROUNDED, show_lines=True)
    table.add_column("#", style="cyan", no_wrap=True)
    table.add_column("Distance", style="magenta")
    table.add_column("Date", style="green")
    table.add_column("Description")
    table.add_column("Path", style="dim")

    for idx, res in enumerate(results, start=1):
        def get_field(item, name):
            return item.get(name) if isinstance(item, dict) else getattr(item, name, None)

        dist = get_field(res, "_distance")
        desc = get_field(res, "description")
        created_at = get_field(res, "created_at")
        path_val = get_field(res, "path")

        dist_str = f"{dist:.4f}" if dist is not None else "N/A"
        date_str = str(created_at)

        table.add_row(str(idx), dist_str, date_str, desc, path_val)

    print(table)

    choices = [str(i) for i in range(1, len(results) + 1)]
    choice = Prompt.ask(
        "Select an image to copy",
        choices=choices + ["q"],
        default="q"
    )

    if choice == "q":
        raise typer.Exit()

    selected_idx = int(choice) - 1
    selected_res = results[selected_idx]

    def get_field(item, name):
        return item.get(name) if isinstance(item, dict) else getattr(item, name, None)

    path_value = get_field(selected_res, "path")
    
    if not path_value:
         print("[red]Result missing file path.[/red]")
         raise typer.Exit(code=1)

    path = Path(path_value)
    if not path.exists():
        print(f"[red]Image file missing at {path}[/red]")
        raise typer.Exit(code=1)

    copy_image_to_clipboard(path)
    print(f"[green]Copied image #{choice} to clipboard from {path}[/green]")


@app.command("delete")
def delete_command():
    """
    Delete the image from the database that matches the image currently in clipboard (by hash).
    """
    try:
        image_bytes = read_image_from_clipboard()
    except ClipboardError as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    file_hash = _hash_bytes(image_bytes)
    print(f"[dim]Clipboard image hash: {file_hash}[/dim]")
    
    db = ImageDB()
    deleted = db.delete_image(file_hash)
    
    if deleted:
        print(f"[green]Deleted image with hash {file_hash} from database and filesystem.[/green]")
    else:
        print(f"[yellow]No image found with hash {file_hash} in database.[/yellow]")
        raise typer.Exit()


def main():
    app()


if __name__ == "__main__":
    main()

