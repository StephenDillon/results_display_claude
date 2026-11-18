"""Strip a Bambu Studio project saved as templates/bambu_p2s_template.3mf down to just its settings.

A project saved from Bambu Studio also contains your models, thumbnails and Bambu account ID
(DesignerUserId). The build only needs the settings, so run this before committing the template:

    python models/strip_template.py [path/to/template.3mf]
"""

import re
import sys
import zipfile
from pathlib import Path

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "templates" / "bambu_p2s_template.3mf"

with zipfile.ZipFile(path) as z:
    settings = z.read("Metadata/project_settings.config")
    slice_info = z.read("Metadata/slice_info.config") if "Metadata/slice_info.config" in z.namelist() else \
        b'<?xml version="1.0" encoding="UTF-8"?>\n<config/>\n'
    model = z.read("3D/3dmodel.model").decode("utf-8")
    before = len(z.namelist())

m = re.search(r'<metadata name="Application">([^<]*)</metadata>', model)
app = m.group(1) if m else "BambuStudio-02.09.01.70"
minimal = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
           'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
           'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021">\n'
           f' <metadata name="Application">{app}</metadata>\n'
           ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n <resources/>\n <build/>\n</model>\n')

with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("3D/3dmodel.model", minimal)
    z.writestr("Metadata/project_settings.config", settings)
    z.writestr("Metadata/slice_info.config", slice_info)

print(f"{path}: {before} entries -> 3 (settings only, {app})")
