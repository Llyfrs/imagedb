# imagedb

> Full Disclaimer ⚠️: this entier project was generated using Cursor. It was just idea I had and it seemed like something AI could do easily. Might properly expand on it if I really enjoy using it. 

Clipboard-first image database with semantic search. Saves images directly from your clipboard, describes them via OpenRouter vision, embeds descriptions, stores vectors in LanceDB, and lets you retrieve images back to your clipboard by text query.

## Features
- `imagedb init` — interactive setup (API key + vision model).
- `imagedb save` — grab PNG from clipboard → describe → embed → store.
- `imagedb load "<query>"` — embed query → vector search → copy best match to clipboard.
- XDG paths: DB in `~/.local/share/imagedb/`, config in `~/.config/imagedb/config.yaml`.
- Clipboard support for Wayland (`wl-copy`, `wl-paste`) and X11 (`xclip`).

## Requirements
- Python 3.13+
- `wl-clipboard` (Wayland) or `xclip` (X11)
- OpenRouter API key

## Install (with uv)
- Editable (recommended for development):  
  `uv pip install -e .`
- Standard install:  
  `uv pip install .`

## Usage
- Initialize config:  
  `uv run imagedb init`
- Save clipboard image to DB (optionally with extra context):  
  `uv run imagedb save` or `uv run imagedb save "Luke Skywalker on Tatooine"`
- Load by text query to clipboard:  
  `uv run imagedb load "a sunset over a lake"`
- View/update config:  
  `uv run imagedb config --show`  
  `uv run imagedb config --api-key sk-or-...`  
  `uv run imagedb config --vision-model google/gemini-2.0-flash-lite-001`

## How to use it system-wide (with `uv tool`)
1) Install once as a tool (copies CLI script into `~/.local/bin`):  
   `uv tool install .`  
   For development / live edits: `uv tool install --editable .`
2) Ensure `~/.local/bin` is on your `PATH` (uv installs tools there). Quickest:  
   `uv tool update-shell`  
   Or manually add to your shell rc: `export PATH="$HOME/.local/bin:$PATH"`
3) Run directly without `uv run`:  
   `imagedb init` / `imagedb save` / `imagedb load "query"`

## Notes
- Vision model default: `google/gemini-2.0-flash-lite-001` (configurable).
- Embedding model is fixed to `qwen/qwen3-embedding-8b` (vector size 4096).
- Images are stored as PNG files under `~/.local/share/imagedb/images/`; hashes prevent duplicates.

