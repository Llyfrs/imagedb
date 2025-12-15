from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class ClipboardError(RuntimeError):
    pass


def _require_tool(tool_name: str) -> None:
    if not shutil.which(tool_name):
        raise ClipboardError(
            "No suitable clipboard utility found (install wl-clipboard or xclip)."
        )


def read_image_from_clipboard() -> bytes:
    """
    Read PNG bytes from the clipboard using wl-paste or xclip.
    Raises ClipboardError if no image data is available.
    """
    if shutil.which("wl-paste"):
        result = subprocess.run(
            ["wl-paste", "--type", "image/png"],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
        raise ClipboardError("No image data found in clipboard (Wayland).")

    if shutil.which("xclip"):
        result = subprocess.run(
            ["xclip", "-selection", "clipboard", "-t", "image/png", "-o"],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
        raise ClipboardError("No image data found in clipboard (X11).")

    _require_tool("wl-paste")  # will raise
    return b""


def copy_image_to_clipboard(image_path: str | Path) -> None:
    """
    Copy a PNG image to the clipboard using wl-copy or xclip.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found at {image_path}")

    if shutil.which("wl-copy"):
        with image_path.open("rb") as f:
            subprocess.run(["wl-copy", "--type", "image/png"], stdin=f, check=True)
        return

    if shutil.which("xclip"):
        with image_path.open("rb") as f:
            subprocess.run(
                ["xclip", "-selection", "clipboard", "-t", "image/png"],
                stdin=f,
                check=True,
            )
        return

    _require_tool("wl-copy")  # will raise

