# README graphics

The wordmark, system diagrams, animation, and case and results graphics share
the same palette. The case image reads the archived Qwen3 trajectory and its
capsule. The results image reads evaluation JSON.

To render them locally, install Pillow 13.0.0 in the project environment and run
`python docs/assets/render.py` from the repository root. The renderer uses
Segoe UI and Consolas on Windows or the DejaVu families when installed.
Pass `--results <path>` to render a different recorded evaluation. The GIF and
its still PNG share the same layout.
