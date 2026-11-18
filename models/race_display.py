"""Race results wall display: parametric build123d model.

Reads ../results.yaml and writes to ../out/ (see main() for the layout).
Print out/display_project.3mf; single tiles are in out/tiles/.

Coordinates: X = width, Y = height on the wall (up), Z = depth (0 = wall side, + toward viewer).
Print orientation is the same as the model: back face (Z=0) on the build plate, text up.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bambu3mf  # noqa: E402
from build123d import (
    Axis, Box, Circle, Color, Compound, Mesher, Polygon, Pos, Rectangle, Text, TextAlign,
    Align, Rot, chamfer, export_gltf, export_step, export_stl, extrude,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
MIN = (Align.MIN, Align.MIN, Align.MIN)

cfg = yaml.safe_load((ROOT / "results.yaml").read_text(encoding="utf-8"))
D, J, K, F, C = cfg["dims"], cfg["joint"], cfg["keyholes"], cfg["fonts"], cfg["colors"]
W, T = D["tile_width"], D["tile_thickness"]
RELIEF = D["text_relief"]
PLATE = 256.0
warnings: list[str] = []


# ---------------------------------------------------------------- text helpers
@dataclass
class FontMetrics:
    path: str
    cap_ratio: float      # cap/digit height per unit font size
    advance: float        # advance per unit font size (meaningful for mono fonts)


def metrics(path: str, probe: str) -> FontMetrics:
    one = Text(probe, 10, font_path=path, text_align=(TextAlign.LEFT, TextAlign.BOTTOM)).bounding_box()
    two = Text(probe * 2, 10, font_path=path, text_align=(TextAlign.LEFT, TextAlign.BOTTOM)).bounding_box()
    return FontMetrics(path, one.max.Y / 10, (two.max.X - one.max.X) / 10)


MONO = metrics(F["mono"], "0")
SANS = metrics(F["sans"], "H")


def text_solid(txt: str, font: FontMetrics, cap: float, x: float, baseline: float, h_align: TextAlign):
    """Raised text sitting on the front face. x is the pen origin (LEFT), end (RIGHT) or center."""
    size = cap / font.cap_ratio
    sk = Text(txt, size, font_path=font.path, text_align=(h_align, TextAlign.BOTTOM))
    return Pos(x, baseline, T) * extrude(sk, RELIEF)


# ---------------------------------------------------------------- joint + keyhole geometry
def joint_xs(width: float, count: int) -> list[float]:
    return [width * (2 * i + 1) / (2 * count) for i in range(count)]


def pocket(clear: float):
    """Dovetail pocket cut up into a tile's bottom edge (open at the back, closed by the front skin)."""
    n, h, d, c = J["neck_width"] / 2 + clear, J["head_width"] / 2 + clear, J["depth"] + clear, clear
    face = Polygon((-n, -1), (n, -1), (n, 0), (h, d), (-h, d), (-n, 0), align=None)
    return extrude(face, T - J["front_skin"])


def tab():
    """Matching dovetail tab standing on a tile's top edge (fused 0.5 mm into the body)."""
    n, h, d = J["neck_width"] / 2, J["head_width"] / 2, J["depth"]
    face = Polygon((-n, -0.5), (n, -0.5), (n, 0), (h, d), (-h, d), (-n, 0), align=None)
    return extrude(face, T - J["front_skin"] - 0.2)


def keyhole(x: float):
    yc, r, w, tr = K["center_height"], K["entry_diameter"] / 2, K["slot_width"], K["slot_travel"]
    neck = Pos(x, yc) * Circle(r) + Pos(x, yc + tr / 2) * Rectangle(w, tr) + Pos(x, yc + tr) * Circle(w / 2)
    cavity = Pos(x, yc) * Circle(r) + Pos(x, yc + tr / 2) * Rectangle(2 * r, tr) + Pos(x, yc + tr) * Circle(r)
    return extrude(neck, K["ledge"] + 0.01) + Pos(0, 0, K["ledge"]) * extrude(cavity, K["head_space"])


def tile_body(width: float, height: float, *, pockets: bool, tabs: bool, joints: int, clear: float, keyholes=False):
    body = Box(width, height, T, align=MIN)
    body = chamfer(body.faces().sort_by(Axis.Z)[-1].edges(), D["face_chamfer"])
    for x in joint_xs(width, joints):
        if pockets:
            body -= Pos(x, 0, 0) * pocket(clear)
        if tabs:
            body += Pos(x, height, 0) * tab()
    if keyholes:
        s = K["spacing"]
        for x in (width / 2 - s / 2, width / 2 + s / 2):
            body -= keyhole(x)
    return body


# ---------------------------------------------------------------- tiles
@dataclass
class Tile:
    name: str
    height: float
    body: object
    text: object | None


def header() -> Tile:
    H = D["header_height"]
    body = tile_body(W, H, pockets=True, tabs=False, joints=J["count"], clear=J["clearance"], keyholes=True)
    rule_y, rule_t = 8.0, 0.8
    cap = D["title_cap_height"]
    baseline = (rule_y + rule_t + H) / 2 - cap / 2
    txt = text_solid(cfg["title"], SANS, cap, W / 2, baseline, TextAlign.CENTER)
    txt += Pos(W / 2 - 30, rule_y, T) * Box(60, rule_t, RELIEF, align=(Align.MIN, Align.MIN, Align.MIN))
    if txt.bounding_box().size.X > W - 2 * D["side_margin"]:
        warnings.append(f"Title '{cfg['title']}' is wider than the tile")
    return Tile("header", H, body, txt)


def result(r: dict) -> Tile:
    H, cap, m = D["tile_height"], D["row_cap_height"], D["side_margin"]
    year, city, time = str(r["year"]), str(r["city"]), str(r["time"])
    body = tile_body(W, H, pockets=True, tabs=True, joints=J["count"], clear=J["clearance"])
    base = H / 2 - cap / 2
    mono_size = cap / MONO.cap_ratio
    city_x = m + 4 * MONO.advance * mono_size + D["year_city_gap"]
    time_x0 = W - m - len(time) * MONO.advance * mono_size
    t_year = text_solid(year, MONO, cap, m, base, TextAlign.LEFT)
    t_city = text_solid(city, SANS, cap, city_x, base, TextAlign.LEFT)
    t_time = text_solid(time, MONO, cap, time_x0, base, TextAlign.LEFT)  # placed by advance -> colons align
    if t_city.bounding_box().max.X > time_x0 - 3:
        warnings.append(f"{year} {city}: city text runs into the time column")
    slug = re.sub(r"[^a-z0-9]+", "_", f"{year}_{city}".lower()).strip("_")
    return Tile(slug, H, body, t_year + t_city + t_time)


def endcap() -> Tile:
    H = D["endcap_height"]
    return Tile("endcap", H, tile_body(W, H, pockets=False, tabs=True, joints=J["count"], clear=0), None)


def joint_test() -> list[tuple[object, object, float, float]]:
    """Three coupon pairs at different clearances. Returns (body, text, x, y) placements."""
    out = []
    for i, c in enumerate((0.10, 0.15, 0.20)):
        label = f"{int(round(c * 100)):02d}"
        x0 = i * 46
        lower = tile_body(40, 16, pockets=False, tabs=True, joints=1, clear=c)
        upper = tile_body(40, 16, pockets=True, tabs=False, joints=1, clear=c)
        for body, y in ((lower, 0), (upper, 28)):
            out.append((body, text_solid(label, MONO, 7, 20, 4.5, TextAlign.CENTER), x0, y))
    return out


# ---------------------------------------------------------------- export
def colored(shape, color: str, label: str):
    shape.color = Color(color)
    shape.label = label
    return shape


TEMPLATE = ROOT / "templates" / "bambu_p2s_template.3mf"


def write_3mf(path: Path, items: list[tuple], plate_of=lambda i: 1):
    """items: (body, text|None, x, y, name). Uses the Bambu Studio template (printer/filament/process
    settings, body -> filament 1, text -> filament 2) when present; plain 3MF otherwise."""
    if TEMPLATE.exists():
        objs = [bambu3mf.Obj(name, [bambu3mf.Part(f"{name}_body", body, 1)]
                             + ([bambu3mf.Part(f"{name}_text", txt, 2)] if txt is not None else []),
                             x, y, plate_of(i))
                for i, (body, txt, x, y, name) in enumerate(items)]
        bambu3mf.write_project(path, objs, TEMPLATE, bed=PLATE,
                               tower_y=PLATE - cfg.get("plate", {}).get("prime_tower_reserve", 60) + 10)
        return
    m = Mesher()
    for body, txt, x, y, name in items:
        m.add_shape(colored(Pos(x, y, 0) * body, C["background"], name), linear_deflection=0.01,
                    angular_deflection=0.2, part_number=f"{name}_body")
        if txt is not None:
            m.add_shape(colored(Pos(x, y, 0) * txt, C["text"], name + "_text"), linear_deflection=0.01,
                        angular_deflection=0.2, part_number=f"{name}_text")
    m.write(str(path))


def clean_outputs():
    """Remove previously generated files only (anything else you put in out/ is left alone)."""
    import shutil
    for d in ("tiles", "preview", "stl"):
        shutil.rmtree(OUT / d, ignore_errors=True)
    for pat in ("display_project.3mf", "joint_test.3mf", "plate_*.3mf", "header.3mf", "endcap.3mf",
                "result_*.3mf", "*_body.stl", "*_text.stl", "assembly.step", "assembly.glb"):
        for f in OUT.glob(pat):
            f.unlink()


def main():
    """Output layout:
      out/display_project.3mf   <- print this (all plates, P2S settings)
      out/joint_test.3mf        <- fit test coupons
      out/tiles/*.3mf           <- one file per tile, for reprints / adding a new race
      out/preview/assembly.*    <- STEP + GLB of the hung display (preview.html)
      out/stl/*.stl             <- only with --stl
    """
    want_stl = "--stl" in sys.argv
    OUT.mkdir(exist_ok=True)
    clean_outputs()
    tiles_dir, preview_dir = OUT / "tiles", OUT / "preview"
    tiles_dir.mkdir(); preview_dir.mkdir()
    if W > PLATE:
        warnings.append(f"tile_width {W} exceeds the P2S plate ({PLATE} mm)")

    tiles = [header()] + [result(r) for r in cfg["results"]] + [endcap()]
    names = []
    for i, t in enumerate(tiles):
        name = t.name if t.name in ("header", "endcap") else f"result_{i:02d}_{t.name}"
        names.append(name)
        write_3mf(tiles_dir / f"{name}.3mf", [(t.body, t.text, (PLATE - W) / 2, 20, name)])
        if want_stl:
            (OUT / "stl").mkdir(exist_ok=True)
            export_stl(t.body, str(OUT / "stl" / f"{name}_body.stl"))
            if t.text is not None:
                export_stl(t.text, str(OUT / "stl" / f"{name}_text.stl"))
    print(f"  tiles/  ({len(tiles)} single-tile 3MFs)")

    # plates: stack tiles front-up on a 256 x 256 plate with 5 mm gaps (footprint includes the 6 mm tab)
    plates, cur, y = [[]], 0, 0.0
    for t, name in zip(tiles, names):
        foot = t.height + (J["depth"] if name != "header" else 0)
        if y + foot > PLATE - cfg.get("plate", {}).get("prime_tower_reserve", 6):
            plates.append([]); cur += 1; y = 0.0
        plates[cur].append((t.body, t.text, (PLATE - W) / 2, y + 3, name))
        y += foot + 5
    if TEMPLATE.exists():
        flat = [it for p in plates for it in p]
        plate_no = [pi for pi, p in enumerate(plates, 1) for _ in p]
        write_3mf(OUT / "display_project.3mf", flat, plate_of=lambda i: plate_no[i])
        print(f"  display_project.3mf ({len(plates)} plates, P2S settings from template)")
    else:  # plain 3MF can't hold several plates
        for i, items in enumerate(plates, 1):
            write_3mf(OUT / f"plate_{i}.3mf", items)
            print(f"  plate_{i}.3mf ({len(items)} tiles)")

    jt = joint_test()
    write_3mf(OUT / "joint_test.3mf", [(b, t, x + 20, y + 20, f"coupon_{k}") for k, (b, t, x, y) in enumerate(jt)])
    print("  joint_test.3mf")

    # assembly as it hangs: header on top, each tile below the previous one
    parts, top = [], 0.0
    for t, name in zip(tiles, names):
        top -= t.height
        parts.append(colored(Pos(0, top, 0) * t.body, C["background"], name))
        if t.text is not None:
            parts.append(colored(Pos(0, top, 0) * t.text, C["text"], name + "_text"))
    asm = Compound(children=parts, label="race_display")
    export_step(asm, str(preview_dir / "assembly.step"))
    export_gltf(Rot(90, 0, 0) * asm, str(preview_dir / "assembly.glb"), binary=True,
                linear_deflection=0.05, angular_deflection=0.3)
    print(f"  preview/assembly.step + .glb  (stack height {-top:.0f} mm)")

    for w in warnings:
        print("WARNING:", w)
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
