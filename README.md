# Sensor Watch Pro Builder

A single-page builder for [Second Movement](https://github.com/joeycastillo/second-movement) firmware on the Sensor Watch Pro. Pick and order watch faces, set defaults, and GitHub Actions compiles a `firmware.uf2` for you.

## Use it

1. Open `index.html` locally, or the GitHub Pages site. To turn Pages on: **Settings → Pages → Source → GitHub Actions**, then run **Deploy builder to Pages** (it also redeploys on every push to `main` that changes the page).
2. Add faces from the catalog to the **Mode rotation** (first face is home) and, optionally, the **Long-press MODE** list (hidden from rotation, reached by holding MODE on the home face).
3. Click the MODE button on the watch preview to step through the rotation exactly as `movement.c` will.
4. Set display type (classic / custom LCD), tune, LED colour, volumes, timeouts.
5. **Commit config to GitHub** opens a pre-filled new file at `configs/<name>.h`. Commit it.
6. The **Build firmware** workflow builds it. Download the `<name>-<display>-firmware` artifact.
7. Double-tap the watch's reset button and copy `firmware.uf2` to the `WATCHBOOT` drive.

Other options: **Copy config** / **Download** to build locally, **Import** to load an existing `movement_config.h`, **Copy share link** to send your setup to someone.

## How the build works

The page writes a normal upstream `movement_config.h` with a metadata header:

```c
 * builder:name=my-watch
 * builder:board=sensorwatch_pro
 * builder:display=classic
 * builder:upstream=<full upstream commit SHA>
 * builder:simulator=no
```

`.github/workflows/build-firmware.yml` runs on any push that adds or changes `configs/*.h` (or manually via **Run workflow**):

| Job | What it does |
|---|---|
| `plan` | Lists changed configs and reads their metadata (`tools/config_meta.py matrix`). |
| `firmware` | Checks out upstream at the pinned SHA with submodules, checks every face exists (`config_meta.py check`), runs `make BOARD=sensorwatch_pro DISPLAY=<display>`, reports flash/RAM use against the 240 KiB app budget, uploads `firmware.uf2` + the config. |
| `simulator` | When `simulator=yes`, builds the Emscripten simulator (`firmware.html/js/wasm`). |

No firmware patches: the build is upstream Second Movement with your config.

## Updating the face catalog

The catalog (faces, descriptions, authors, tunes, upstream default) is embedded in `index.html` between `/*CATALOG-BEGIN*/` and `/*CATALOG-END*/`, and mirrored to `catalog.json`.

```sh
git clone --recurse-submodules https://github.com/joeycastillo/second-movement.git /tmp/sm
python3 tools/sync_catalog.py /tmp/sm          # rewrite catalog + pin the new upstream SHA
python3 tools/sync_catalog.py /tmp/sm --check  # CI-style: fail if index.html is stale
node tests/builder.test.js /tmp/sm             # browser tests (needs Playwright)
```

Faces are read from the `#include "*_face.h"` lines of `movement_faces.h`, not from a glob, so support headers are never listed. Configs reference faces by name, so adding or reordering faces upstream never breaks an existing config; a removed face fails the `check` step with a clear error.

## Custom faces

Faces that are not in upstream live in `faces/<category>/<name>_face.{c,h}`, where `<category>` is an upstream `watch-faces/` folder (`io`, `demo`, `sensor`, …). Before the face check and compile, the workflow runs `tools/custom_faces.py apply fw`. This copies them into the upstream checkout and registers them in `watch-faces.mk` and `movement_faces.h`. `sync_catalog.py` adds them to the catalog with `"custom": true`, so the builder lists them. Pushing a change under `faces/` rebuilds every config that uses a custom face.

| Face | Purpose |
|---|---|
| `ir_peak_face` | IR sensor test: live ADC reading plus MIN/MAX hold (ALARM cycles, LIGHT resets). Sensor Watch Pro only. |

To build locally, run `python3 tools/custom_faces.py apply <second-movement>` before `make`.

## Tests

`tests/builder.test.js` loads the page in Chromium and checks that:

- the **Upstream default** preset reproduces upstream's `movement_config.h` (faces, secondary index, every `#define`);
- `config_meta.py` accepts the generated file and reads its metadata;
- generate → import → generate is stable, including duplicates and long-press faces;
- the MODE / long-press simulator matches `movement_move_to_next_face()` and `EVENT_MODE_LONG_PRESS`;
- the catalog buttons and GitHub commit link work, with no page errors.

## Files

| Path | Purpose |
|---|---|
| `index.html` | The builder (single file, works offline) |
| `.github/workflows/pages.yml` | Publishes `index.html` + `catalog.json` to GitHub Pages |
| `catalog.json` | Same catalog as embedded in the page |
| `configs/` | Committed watch configs; each push builds firmware |
| `tools/sync_catalog.py` | Regenerates the catalog from an upstream checkout |
| `tools/config_meta.py` | Workflow helper: metadata matrix and face check |
| `faces/` | Custom faces not in upstream (see above) |
| `tools/custom_faces.py` | Adds `faces/` to an upstream checkout before building |
| `tests/builder.test.js` | Browser tests |
