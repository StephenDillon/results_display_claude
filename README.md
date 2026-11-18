# Race Results Wall Display

A modular, 3D-printable wall display for your race results. A header tile shows the title (e.g. **MARATHON**). Below it, each race gets its own tile:

```
 ┌────────────────────────────────────────────┐
 │                  MARATHON                  │  ← header (hangs on 2 screws)
 ├────────────────────────────────────────────┤
 │ 2008  Dublin                       3:41:19 │  ← one tile per race
 │ 2009  Cork                         3:29:57 │
 │ ...                                    ... │
 │ 2026  Charlotte                    4:29:29 │
 └────────────────────────────────────────────┘
```

- **Year** is left-aligned and **time** is right-aligned, both in a monospaced font so the digits and colons line up down the stack. The **city** name follows the year.
- Tiles **lock together** with hidden dovetails. Press a new tile in from behind, and it can't fall down, slide sideways or tip forward off the wall.
- **Grows over time:** after each new race, print one more tile and add it to the bottom.
- **Two colors**, black body with raised white text by default. Both are set in a config file.
- Built for **Bambu Lab printers** (P2S, 256 mm plate) with an AMS. The output files open in Bambu Studio with the printer, process and filament already set up.

The model is fully parametric Python using [build123d](https://github.com/gumyr/build123d). It was made with [text-to-cad](https://github.com/earthtojake/text-to-cad) and Claude Code. See [specs.md](specs.md) for the full design spec.

The example data in [results.yaml](results.yaml) is my own marathon history. Replace it with yours. Ready-to-print example files are attached to the [latest release](https://github.com/StephenDillon/results_display_claude/releases/latest).

---

## Make your own with Claude (or another AI agent)

If you'd rather not run things by hand, open this repo in [Claude Code](https://claude.com/claude-code) (or any agent that reads `AGENTS.md`) and say something like:

> Make me a display with my marathon results: 2019 Berlin 3:41:07, 2023 Chicago 3:29:15. I'm on a Mac with a Bambu A1.

[AGENTS.md](AGENTS.md) tells the agent what to do. It asks for anything missing, sets up Python, picks fonts for your OS, adapts to your printer, builds the files, and tells you what to print.

## Make your own by hand

### 1. Install

You need Python **3.10–3.12**. The CAD kernel build123d depends on may not support newer Python versions yet; it failed to install on 3.14 when this was built.

```bash
git clone https://github.com/StephenDillon/results_display_claude.git
cd results_display_claude
python -m venv .venv
# Windows
.venv\Scripts\pip install -r requirements.txt
# macOS / Linux
.venv/bin/pip install -r requirements.txt
```

(With [uv](https://docs.astral.sh/uv/): `uv venv --python 3.12 .venv && uv pip install --python .venv -r requirements.txt`.)

### 2. Enter your results

Edit [results.yaml](results.yaml):

```yaml
title: MARATHON

results:            # oldest at the top, newest at the bottom
  - { year: 2019, city: Berlin,  time: "3:41:07" }
  - { year: 2023, city: Chicago, time: "3:29:15" }
```

- Put `time` in quotes, written as `H:MM:SS`.
- Keep city names short. The build warns you if one would run into the time.
- `title` can be anything that fits, e.g. `HALF MARATHON` or `ULTRA`.

### 3. Set the fonts for your OS

The defaults are Windows system fonts (Consolas Bold + Segoe UI Bold). On macOS or Linux, point `fonts:` at any `.ttf` files. A **monospaced** font is required for `mono`:

```yaml
fonts:
  mono: /path/to/JetBrainsMono-Bold.ttf   # free: https://www.jetbrains.com/lp/mono/
  sans: /path/to/Inter-Bold.ttf           # free: https://rsms.me/inter/
```

### 4. Build

```bash
# Windows
.venv\Scripts\python models/race_display.py
# macOS / Linux
.venv/bin/python models/race_display.py
```

This takes about 20 seconds and writes:

```
out/
├── display_project.3mf   ← print this: every tile laid out on plates, settings included
├── joint_test.3mf        ← small coupons to check the joint fit (print first)
├── tiles/                ← one file per tile, for reprints or adding a new race
└── preview/              ← assembly.glb / .step of the finished display
```

To see the finished display in 3D, serve the folder (`python -m http.server`) and open `preview.html`.

### 5. Match your printer (optional, recommended)

The 3MFs take their printer, process and filament settings from [templates/bambu_p2s_template.3mf](templates/bambu_p2s_template.3mf). That file is set up for a **Bambu Lab P2S, 0.4 nozzle, 0.20 mm Standard, Textured PEI, PETG black (slot 1) + white (slot 2)**.

To use your own printer and filaments:
1. Open any project in Bambu Studio and pick your printer, plate, process and two filaments. The body uses **filament 1** and the text uses **filament 2**.
2. **File → Save Project As…** and save over `templates/bambu_p2s_template.3mf`.
3. Run `python models/strip_template.py` (using your venv's Python). It strips the saved project down to just its settings, which removes your Bambu account ID, models and thumbnails. Do this before you commit the file anywhere.
4. Rebuild.

On a printer with a smaller bed, also lower `tile_width` in `results.yaml` (e.g. 175 for a 180 mm bed). If you delete the template, the build writes plain 3MFs instead, which any slicer can open.

### 6. Print

1. **Test the joint fit first.** Print `out/joint_test.3mf`. It makes three pairs labeled 10 / 15 / 20 (gaps of 0.10, 0.15 and 0.20 mm). Pick the pair that presses together firmly with no wobble, and set `joint.clearance` in `results.yaml` to that value. 0.15 worked for me with PETG on a P2S.
2. **Print the display.** Open `out/display_project.3mf` and slice each plate.
   - Tiles print face-up with no supports.
   - The white is only the top 0.8 mm of text, so each plate has just **one** color change. If you'd rather not print the prime tower, you can turn it off.
3. **Assemble.** Lay the tiles face-down in order: header first, then oldest to newest, then the end cap. Press each tile's tabs into the pockets of the tile above it.

### 7. Hang it

- Put two screws (#8 / M4, head ≤ 8.5 mm) in the wall, **200 mm apart and level**, with the heads sticking out about 3 mm.
- Hook the header's keyholes over the screws and let the display slide down.

The example display (9 races) is 250 × 264 mm.

### Adding a race later

1. Add the new line at the bottom of `results.yaml` and rebuild.
2. Print just the newest file in `out/tiles/`.
3. Take the display off the wall, pull off the end cap, press the new tile in, put the end cap back, and hang it up again.

---

## Customizing

Every dimension is in [results.yaml](results.yaml):

| Setting | Default | What it does |
|---|---|---|
| `dims.tile_width` | 250 | Overall width (mm). The P2S plate is 256 mm |
| `dims.tile_height` / `header_height` | 24 / 40 | Height of each race tile / the header |
| `dims.row_cap_height` / `title_cap_height` | 9 / 16 | Text size (height of capital letters and digits) |
| `dims.text_relief` | 0.8 | How far the text stands out from the face |
| `joint.clearance` | 0.15 | Joint fit gap per side. Tune with the test coupons |
| `keyholes.spacing` | 200 | Distance between the wall screws |
| `plate.prime_tower_reserve` | 60 | Strip left free on each plate for the prime tower |
| `colors.*` | black / white | Colors shown in the preview. The actual print colors come from the filaments you load |

## Files

| Path | What |
|---|---|
| `models/race_display.py` | The parametric model and the export step |
| `models/bambu3mf.py` | Writes Bambu Studio project 3MFs using the settings template |
| `models/strip_template.py` | Strips a saved Bambu project down to settings only |
| `AGENTS.md` / `CLAUDE.md` | Instructions for AI agents building a display for you |
| `out/` | Build output. It isn't committed; regenerate it, or download the examples from Releases |
| `results.yaml` | Your data and all parameters |
| `specs.md` | Design spec (layout, joint, mounting, printing) |
| `mockups.html` | The early 2D mockups. The joint drawings show the older v0.2 design |
| `preview.html` | 3D viewer for `out/preview/assembly.glb` |
