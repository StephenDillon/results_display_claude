"""Write Bambu Studio project 3MFs that carry the printer/process/filament settings
from a template 3MF saved by Bambu Studio (templates/bambu_p2s_template.3mf).

Each tile becomes its own object with two parts: body -> filament 1, text -> filament 2.
Plates are laid out the way Bambu Studio does it: plate n is offset in X by n * width * 1.2.
"""

from __future__ import annotations

import json
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from build123d import Mesher

NS3MF = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"
PLATE_STRIDE = 1.2  # Bambu Studio LOGICAL_PART_PLATE_GAP = 1/5


@dataclass
class Part:
    name: str
    shape: object
    extruder: int


@dataclass
class Obj:
    name: str
    parts: list[Part]
    x: float          # where the object's local origin goes on its plate
    y: float
    plate: int = 1    # 1-based


def _mesh(shape, lin=0.01, ang=0.2):
    """Tessellate via build123d's Mesher (watertight, merged vertices) and read it back."""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "m.3mf"
        m = Mesher()
        m.add_shape(shape, linear_deflection=lin, angular_deflection=ang)
        m.write(str(p))
        with zipfile.ZipFile(p) as z:
            root = ET.fromstring(z.read("3D/3dmodel.model"))
    verts, tris = [], []
    for mesh in root.iter(f"{NS3MF}mesh"):
        base = len(verts)
        verts += [(float(v.get("x")), float(v.get("y")), float(v.get("z"))) for v in mesh.iter(f"{NS3MF}vertex")]
        tris += [(base + int(t.get("v1")), base + int(t.get("v2")), base + int(t.get("v3")))
                 for t in mesh.iter(f"{NS3MF}triangle")]
    return verts, tris


def _u():
    return str(uuid.uuid4())


HEAD = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
        'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
        'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">\n')


def write_project(path: Path, objects: list[Obj], template: Path, bed: float = 256.0, tower_y: float = 210.0):
    with zipfile.ZipFile(template) as t:
        settings = json.loads(t.read("Metadata/project_settings.config"))
        slice_info = t.read("Metadata/slice_info.config")
        tmpl_root = ET.fromstring(t.read("3D/3dmodel.model"))
    app = next((m.text for m in tmpl_root.iter(f"{NS3MF}metadata") if m.get("name") == "Application"),
               "BambuStudio-02.09.01.70")

    n_plates = max(o.plate for o in objects)
    # one prime-tower position per plate, in the free strip at the top of the bed
    tx = settings.get("wipe_tower_x", ["165"])[0]
    settings["wipe_tower_x"] = [tx] * n_plates
    settings["wipe_tower_y"] = [str(tower_y)] * n_plates

    files: dict[str, str | bytes] = {}
    main_objs, build_items, rels, ms_objs = [], [], [], []
    plates: dict[int, list[int]] = {}
    next_id = 1
    for k, o in enumerate(objects, 1):
        sub = f"3D/Objects/object_{k}.model"
        sub_xml, comps, ms_parts, faces_total = [], [], [], 0
        for part in o.parts:
            verts, tris = _mesh(part.shape)
            faces_total += len(tris)
            pid = next_id; next_id += 1
            vx = "".join(f'     <vertex x="{x:.5f}" y="{y:.5f}" z="{z:.5f}"/>\n' for x, y, z in verts)
            tx_ = "".join(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>\n' for a, b, c in tris)
            sub_xml.append(f'  <object id="{pid}" p:UUID="{_u()}" type="model">\n   <mesh>\n    <vertices>\n{vx}'
                           f'    </vertices>\n    <triangles>\n{tx_}    </triangles>\n   </mesh>\n  </object>\n')
            comps.append(f'    <component p:path="/{sub}" objectid="{pid}" p:UUID="{_u()}" '
                         f'transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n')
            ms_parts.append(
                f'    <part id="{pid}" subtype="normal_part">\n'
                f'      <metadata key="name" value="{escape(part.name)}"/>\n'
                f'      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n'
                f'      <metadata key="extruder" value="{part.extruder}"/>\n'
                f'      <mesh_stat face_count="{len(tris)}" edges_fixed="0" degenerate_facets="0" '
                f'facets_removed="0" facets_reversed="0" backwards_edges="0"/>\n    </part>\n')
        files[sub] = HEAD + ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n <resources>\n' + \
            "".join(sub_xml) + ' </resources>\n <build/>\n</model>\n'
        rels.append(f' <Relationship Target="/{sub}" Id="rel-{k}" '
                    'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n')

        oid = next_id; next_id += 1
        main_objs.append(f'  <object id="{oid}" p:UUID="{_u()}" type="model">\n   <components>\n'
                         + "".join(comps) + '   </components>\n  </object>\n')
        px = o.x + (o.plate - 1) * bed * PLATE_STRIDE
        build_items.append(f'  <item objectid="{oid}" p:UUID="{_u()}" '
                           f'transform="1 0 0 0 1 0 0 0 1 {px:.4f} {o.y:.4f} 0" printable="1"/>\n')
        ms_objs.append(f'  <object id="{oid}">\n    <metadata key="name" value="{escape(o.name)}"/>\n'
                       f'    <metadata key="extruder" value="1"/>\n    <metadata face_count="{faces_total}"/>\n'
                       + "".join(ms_parts) + '  </object>\n')
        plates.setdefault(o.plate, []).append(oid)

    meta = "".join(f' <metadata name="{k}">{escape(v)}</metadata>\n' for k, v in [
        ("Application", app), ("BambuStudio:3mfVersion", "1"), ("Title", path.stem)])
    files["3D/3dmodel.model"] = HEAD + meta + " <resources>\n" + "".join(main_objs) + \
        f' </resources>\n <build p:UUID="{_u()}">\n' + "".join(build_items) + " </build>\n</model>\n"
    files["3D/_rels/3dmodel.model.rels"] = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships '
        'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n' + "".join(rels) + "</Relationships>\n")

    plate_xml = []
    ident = 1000
    for pn in range(1, n_plates + 1):
        inst = ""
        for oid in plates.get(pn, []):
            ident += 1
            inst += (f'    <model_instance>\n      <metadata key="object_id" value="{oid}"/>\n'
                     f'      <metadata key="instance_id" value="0"/>\n'
                     f'      <metadata key="identify_id" value="{ident}"/>\n    </model_instance>\n')
        plate_xml.append(f'  <plate>\n    <metadata key="plater_id" value="{pn}"/>\n'
                         f'    <metadata key="plater_name" value=""/>\n    <metadata key="locked" value="false"/>\n'
                         f'    <metadata key="filament_map_mode" value="Auto For Flush"/>\n{inst}  </plate>\n')
    files["Metadata/model_settings.config"] = ('<?xml version="1.0" encoding="UTF-8"?>\n<config>\n'
                                               + "".join(ms_objs) + "".join(plate_xml) + "</config>\n")
    files["Metadata/project_settings.config"] = json.dumps(settings, indent=4)
    files["Metadata/slice_info.config"] = slice_info
    files["Metadata/filament_sequence.json"] = json.dumps(
        {f"plate_{i}": {"nozzle_sequence": [], "optimal_assignment": [], "sequence": []} for i in range(1, n_plates + 1)})
    files["[Content_Types].xml"] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
        ' <Default Extension="png" ContentType="image/png"/>\n'
        ' <Default Extension="gcode" ContentType="text/x.gcode"/>\n</Types>\n')
    files["_rels/.rels"] = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships '
        'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n</Relationships>\n')

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in ["[Content_Types].xml", "_rels/.rels"] + [n for n in files if n not in ("[Content_Types].xml", "_rels/.rels")]:
            data = files[name]
            z.writestr(name, data if isinstance(data, bytes) else data.encode("utf-8"))
