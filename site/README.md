# Project site

The site is a static GitHub Pages artifact. The build replays the featured
trajectory and reads the experiment results before generating HTML.
The architecture, replay, and results remain available with JavaScript disabled.

With the editable Python package installed, run `python site/build.py`.
Serve `dist/site` with `python -m http.server --directory dist/site`.
The production workflow deploys the same output from the default branch.
Run `pytest tests/test_site.py` to verify the build, local links, metadata,
and replay evidence. To regenerate the social image, install Pillow and run
`python site/branding.py`.
