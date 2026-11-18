# Race Results Wall Display — Specification

Status: **v0.3**. The CAD model is built (`models/race_display.py`) and the joint is redesigned (§4)
Target toolchain: [text-to-cad](https://github.com/earthtojake/text-to-cad) (Python + build123d) → 3MF/STEP/STL → Bambu Studio → Bambu Lab printer / MakerWorld

---

## 1. Concept

A modular, wall-hung display of race results. It is a vertical stack of printed tiles:

- **Header tile** (one): shows a centered title, e.g. `MARATHON`. It holds the wall-mount keyholes and carries the weight of the stack.
- **Result tiles** (one per race, ordered oldest at top → newest at bottom): each one shows `<year>  <city>  <time>`. Each tile hangs from the tile above it.
- **End cap** (optional, one): a thin strip that covers the bottom connector of the last tile.

Adding a race means printing one more result tile and sliding it onto the bottom of the stack.

```
 ┌──────────────────────────────────┐  ◄ keyhole   keyhole ►
 │             MARATHON             │   Header tile
 ├──────────────────────────────────┤   ── sliding dovetail joint
 │ 2008  Dublin              3:41:19│   Result tile
 ├──────────────────────────────────┤
 │ 2009  Cork                3:29:57│   Result tile
 ├──────────────────────────────────┤
 │ 2026  Charlotte           4:29:29│   Result tile
 └──────────────────────────────────┘
        (optional end cap)
```

## 2. Layout and Typography

### 2.1 Header tile
- The title is centered horizontally and vertically.
- The title is uppercase by default and can be configured. A wide, bold sans font is used.
- Optional thin horizontal rule under the title (on by default).

### 2.2 Result tile
| Field | Alignment | Font | Notes |
|---|---|---|---|
| Year | Left, at left margin | **Monospaced** | Always 4 digits |
| City | Left, starts a fixed distance after the year column | Proportional sans | Truncate or warn if it would collide with the time |
| Time | **Right**, at right margin | **Monospaced** | `H:MM:SS` format. All times are padded to the same width (e.g. `3:41:07`), so the colons line up |

- The year and time use the **same monospaced font and size** on every tile. This lines up the digits and colons vertically down the stack.
- The year column has a fixed width, so every city name starts at the same x position.
- Text baseline is vertically centered in the visible face of the tile.

### 2.3 Fonts (defaults, configurable)
- Monospaced (year, time): **Consolas Bold** (`C:/Windows/Fonts/consolab.ttf`). JetBrains Mono Bold (OFL) is a drop-in alternative if you want to share the source files
- Proportional (title, city): **Segoe UI Bold** (`segoeuib.ttf`). Inter Bold (OFL) is an alternative
- Font paths are set in `results.yaml` (`fonts.mono`, `fonts.sans`) and passed to build123d `Text(font_path=...)`.

## 3. Dimensions (defaults, all parametric)

| Parameter | Default | Notes |
|---|---|---|
| `tile_width` | 250 mm | Sized for the **Bambu Lab P2S** (256 × 256 mm plate). About 3 mm per side is left for the brim/skirt. 256 is the hard maximum |
| `header_height` | 40 mm | Visible face height |
| `tile_height` | 24 mm | Visible face height of a result tile |
| `tile_thickness` | 8 mm | Total depth, back to front face (not counting text) |
| `text_relief` | 0.8 mm | How far the text stands out from the face. **Decided: raised text** |
| `title_cap_height` | 16 mm | |
| `row_cap_height` | 9 mm | Year, city and time |
| `side_margin` | 8 mm | Distance from the edge to the year and to the time |
| `year_city_gap` | 6 mm | Gap after the year column |
| `corner_radius` | 1.5 mm | Front-face outer corners on the header, and on the bottom of the last tile/end cap |
| `face_chamfer` | 0.4 mm | Small chamfer on the front edges. It hides the seams between tiles |

## 4. Tile-to-Tile Connection

**Requirements:** each tile must hang reliably from the one above. It must not come off downward or forward. The stack must be expandable without tools, and the seam on the front face should be nearly invisible.

**Design: rear-insert dovetails behind a front skin** (revised in v0.3, see note)

- **Top edge of each result tile (and the end cap):** `count` = 3 **dovetail tabs** (trapezoids in the face plane) stand 6 mm up from the edge. They sit at 1/6, 1/2 and 5/6 of the width.
- **Bottom edge of each tile (including the header):** matching **dovetail pockets**. They are open at the **back** and at the bottom edge, and closed at the front by a 2 mm **front skin**. Tabs are 0.2 mm thinner than the pockets are deep.
- **Assembly:** lift the display off the wall, lay it face-down, and drop the new tile's tabs into the pockets from behind. Then hang it back up.
- **Retention once it's on the wall:**
  - Down (gravity): the dovetail heads catch under the pocket shoulders.
  - Sideways: also held by the dovetail shape.
  - Forward: the front skin blocks the tabs.
  - Backward: the wall blocks the tile.
  - No detents or pins needed.
- The joint is completely hidden from the front. The only visible line is the 0.4 mm chamfer seam.

| Joint parameter | Default |
|---|---|
| `neck_width` / `head_width` | 10 / 16 mm |
| `depth` (tab height) | 6 mm |
| `front_skin` | 2 mm |
| `clearance` | 0.15 mm per side (**confirmed by test print**: the 0.15 coupon fit best) |

> **Why it changed from v0.2:** the earlier design was a side-sliding dovetail whose profile ran front-to-back. It can't be printed face-up without supports, because one flank of either the rail or the channel always becomes an unsupported overhang. In the new design all joint walls are vertical when printed. The only overhang is the front skin over each pocket, which is a short (~16 mm) bridge.

## 5. Wall Mounting

- The **header tile** has **two keyhole slots** in its back face, `keyhole_spacing` = 200 mm apart and centered.
  - Head hole Ø 9 mm, slot width 4.5 mm, slot length 8 mm upward. Recess depth 4 mm, with a 2.5 mm undercut ledge for the screw head.
  - Fits #8 / M4 pan-head or flat-head wood screws with heads up to 8.5 mm.
  - The keyholes are **blind** (no hole through the front face).
- **Optional:** a single centered keyhole on any result tile (`tile_keyhole = true`). Use it for tall stacks (> ~10 tiles) or for an extra anchor at the bottom.
- The back face is flat so the display sits flush on the wall. An optional 1 mm standoff ring around each keyhole helps on textured walls.

## 6. Colors and Multi-Material

- Two colors, **both configurable**:
  - `background_color` (default **black**). This is the tile body.
  - `text_color` (default **white**). This is the raised text and the optional rule.
- The model is exported as a **multi-part 3MF**. Each tile has two named bodies, `body` and `text`, so Bambu Studio can assign filaments directly with the AMS.
- Non-AMS fallback: the text is raised and starts at a single Z height. You can then use **one manual filament change at a layer height** (Bambu Studio "Add pause / change filament" at `tile_thickness`).
- Colors in the 3MF are stored as display colors only. The actual color comes from the filament the user picks.

## 7. Printing (Bambu Lab / MakerWorld)

- **Orientation:** back face on the build plate, front face up. The text prints as the top layers, which gives crisp text and a smooth back on the wall.
- Material: PLA or PLA Matte (recommended, because it reduces glare). PETG is fine.
- 0.4 mm nozzle, 0.2 mm layers (0.12 mm for the text layers if you use variable layer height). 3 walls, 15% infill.
- No supports needed. The joint walls are vertical, the pocket skins bridge about 16 mm, and the keyhole cavities bridge 9 mm.
- **MakerWorld:** publish the 3MF with a plate per tile type (header, sample result tiles, end cap, joint test coupon). Optionally publish a **Parametric Model Maker** version later, so people can type their own year/city/time online.

## 8. Deliverables

1. `models/race_display.py` is the build123d script. It is fully parametric and driven by a data file.
2. `results.yaml` is the input data:
   ```yaml
   title: MARATHON
   colors: { background: "#000000", text: "#FFFFFF" }
   results:
     # sorted oldest → newest; new races are added at the bottom
     - { year: 2008, city: Dublin,      time: "3:41:19" }
     - { year: 2009, city: Cork,        time: "3:29:57" }
     - { year: 2009, city: NYC,         time: "3:41:50" }
     - { year: 2010, city: Cork,        time: "3:33:16" }
     - { year: 2010, city: Dublin,      time: "4:12:57" }
     - { year: 2024, city: Charlotte,   time: "4:51:14" }
     - { year: 2026, city: Rome,        time: "4:10:39" }
     - { year: 2026, city: Marine Corp, time: "5:01:42" }
     - { year: 2026, city: Charlotte,   time: "4:29:29" }
   ```
3. Output files:
   - `header.3mf`
   - One `result_<year>_<city>.3mf` per race
   - `endcap.3mf`
   - `joint_test.3mf`: a small test piece, two 30 mm dovetail sections, used to tune `joint_clearance`
   - `assembly.step`/`.glb` for previewing the whole stack
4. A validation step that fails or warns if the city text overlaps the time column, or if the tile is wider than the selected printer's bed.

## 9. Open Questions

1. ~~Raised or inlaid text?~~ **Decided: raised.**
2. ~~Width?~~ **Decided: 250 mm (P2S).** Is a 24 mm tile height right? Do you also want an optional distance label, or a PR/medal marker?
3. Time format: always `H:MM:SS`, or allow `MM:SS` for shorter races, padded to the same width?
4. Should the stack hang only from the header, or should every tile get a keyhole?
5. Should the slide direction (open end left or right) be configurable?
