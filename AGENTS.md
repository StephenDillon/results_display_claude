# AGENTS.md: building a race results display for someone

These are instructions for an AI coding agent (Claude Code, Codex, etc.) helping a user make their own copy of this display. The user may not know Python or CAD. Your job is to collect their details, set things up, build the files, and hand them back something ready to print.

Read [README.md](README.md) for the human-facing version and [specs.md](specs.md) for the design rationale.

## What this project is

- `results.yaml` holds all the user data and parameters.
- `models/race_display.py` (build123d) builds stackable wall tiles from that file:
  - a header with the title and two keyholes,
  - one tile per race (`year` left, `city` after it, `time` right-aligned, year and time in a monospace font),
  - an end cap.
- Tiles join with hidden rear-insert dovetails.
- The output is Bambu Studio project 3MFs. They take their printer, process and filament settings from `templates/bambu_p2s_template.3mf`. Body parts use filament 1 and text parts use filament 2.

## Workflow

### 1. Ask the user for (only what you can't infer)

1. **Their results.** For each race: year, city or race name, finish time. Accept any format they paste (a list, CSV, a running-app export, prose), then normalize it:
   - `time` as a quoted `"H:MM:SS"` string (`"3:05:09"`, not `"3:5:9"`).
   - `city` short, without the word "Marathon", because the header already says it.
   - Sorted oldest → newest. Within a year, order by race date if you know it, otherwise ask.
   - Confirm the normalized list back to them before building.
2. **Title**, for example `MARATHON` or `HALF MARATHON`.
3. **Printer.** If it isn't a Bambu Lab P2S (256 mm plate), see step 4.
4. **Their OS.** This decides which fonts to use (step 3).

Don't ask about dimensions, joints or colors unless the user brings them up. The defaults have been test-printed.

### 2. Set up Python

The build needs Python **3.10–3.12**, because the CAD kernel may not install on newer versions. Use a project-local venv:

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv -r requirements.txt
# or: python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt   (Windows: .venv\Scripts\pip)
```

Check it with `python -c "import build123d"` using the venv's Python.

On Windows, a `DLL load failed ... Application Control policy has blocked this file` error comes from Smart App Control blocking a fresh numpy/scipy build. The pinned versions in `requirements.txt` avoid it. **Never** suggest turning off Smart App Control or any other security setting.

### 3. Fonts

`fonts.mono` **must be a monospaced font**, or the times won't line up. The defaults are Windows system fonts:

| OS | `mono` | `sans` |
|---|---|---|
| Windows | `C:/Windows/Fonts/consolab.ttf` | `C:/Windows/Fonts/segoeuib.ttf` |
| macOS | a bold mono `.ttf` the user has installed, e.g. `~/Library/Fonts/JetBrainsMono-Bold.ttf` (system Menlo is a `.ttc`, so use a `.ttf` instead) | `/System/Library/Fonts/Supplemental/Arial Bold.ttf` |
| Linux | `/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf` | `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf` |

Look for the files on the user's machine before you write the paths. If no suitable mono `.ttf` exists, ask the user before downloading one. JetBrains Mono and Inter are both free under the OFL licence.

### 4. Printer settings template

- **Bambu P2S with an AMS:** use the committed template as it is. It's set to PETG, black in slot 1 and white in slot 2. Tell the user to load filaments to match, or to change them in Bambu Studio after opening the file.
- **Other Bambu printer, or other filaments:** ask the user to open Bambu Studio, pick their printer, plate, process and two filaments, then **File → Save Project As** over `templates/bambu_p2s_template.3mf` (or anywhere, and you copy it in). Then run:
  ```bash
  .venv/bin/python models/strip_template.py
  ```
  This removes their Bambu account ID (`DesignerUserId`), thumbnails and models. Only the settings stay. Do this **before** any commit.
- **Smaller bed:** set `dims.tile_width` to about the bed width minus 6 mm.
- **Non-Bambu slicer:** delete or rename the template. The build then writes plain 3MFs (one per plate). The user assigns body and text colors in their slicer.

### 5. Build and check

```bash
.venv/bin/python models/race_display.py        # Windows: .venv\Scripts\python
```

- The build takes about 20 seconds.
- It exits non-zero and prints `WARNING:` lines when something doesn't fit:
  - **A city name runs into the time:** shorten or abbreviate the city (ask the user), or raise `tile_width` if the bed allows.
  - **The title is too wide:** shorten the title or lower `title_cap_height`.
  - **The tile is wider than the plate:** lower `tile_width`.
- Optional visual check: serve the repo folder (`python -m http.server`) and open `preview.html`. It loads `out/preview/assembly.glb`.

### 6. Hand off to the user

Point them at the outputs and tell them, in this order:

1. **Print `out/joint_test.3mf` first.** It makes three coupon pairs labeled 10 / 15 / 20 (gaps of 0.10, 0.15 and 0.20 mm). Have them pick the pair that presses together firmly without wobbling. If it isn't 0.15, set `joint.clearance` to that value and rebuild.
2. **Print `out/display_project.3mf`.** It has all the plates, prints face-up with no supports, and has a single color change per plate.
3. **Assemble face-down:** header, then tiles oldest → newest, then the end cap. Press the tabs into the pockets from behind.
4. **Hang it on two screws `keyholes.spacing` apart** (200 mm by default), level, with heads sticking out about 3 mm.

To add a race later, append it to `results.yaml`, rebuild, and print only the newest file in `out/tiles/`.

## Rules

- **Don't commit `out/`** (it's gitignored). Example print files go on GitHub Releases.
- **Don't commit `.venv/` or `.claude/`.**
- Before committing a template the user saved, run `models/strip_template.py` and check it lists only 3 entries.
- Results are personal data. Only push them to a public repo if the user says so.
- **Don't change the joint geometry casually.** It was redesigned so it prints with no supports (see specs.md §4) and tuned with a test print. If you change `joint.*` or `tile_thickness`, have the user print `joint_test.3mf` again.
- `mockups.html` shows an older joint design. Treat `specs.md` §4 and the code as the source of truth.

## Code map

| File | Notes |
|---|---|
| `models/race_display.py` | `header()`, `result()` and `endcap()` build each tile. `pocket()` and `tab()` are the joint. `keyhole()` is the wall mount. `main()` handles plate packing and exports |
| `models/bambu3mf.py` | Writes Bambu project 3MFs: one object per tile, body on filament 1, text on filament 2. Plate n is offset by `n × bed × 1.2` in X |
| `models/strip_template.py` | Reduces a saved Bambu project to settings only |
| `results.yaml` | All data and parameters |
| `templates/bambu_p2s_template.3mf` | Printer, process and filament settings only |

Coordinates: X is width, Y is up on the wall, Z is depth (0 = wall side). The print orientation matches the model: back face on the plate.
