# Layout Planner 1.0 — QGIS plugin

Native desktop plugin for planning two or three maps on one editable QGIS print layout. Designed for QGIS 3.34+ and QGIS 4 / Qt 6. Uses only QGIS and its bundled Python/Qt libraries. No pip, Conda, account, hosted service or GPU is required.

## Install

1. Keep `Layout_Planner_QGIS_v1.0.0.zip` zipped.
2. QGIS → Plugins → Manage and Install Plugins → Install from ZIP.
3. Choose the ZIP and click Install Plugin. Enable **Layout Planner** if necessary.
4. Open it from its toolbar icon or Plugins → Layout Planner → Layout Planner.

Roman Urdu: ZIP extract nahi karni. QGIS ke **Install from ZIP** mein file select karke install karein.

## Use

1. Load your layers in QGIS. Turn on the layers and zoom to the view wanted for the first map.
2. Open Layout Planner. Choose A5, A4, A3, Letter or Legal and orientation. Choose two or three map frames and an arrangement. Set margins and spacing.
3. Select a frame. Drag to move, drag any corner to resize, or enter X, Y, Width and Height in mm. The origin is the page's top-left. Frames are constrained inside the margins, with a 20 × 20 mm minimum. Overlaps are allowed and visibly flagged.
4. For independent map views, keep the planner open, switch to the main QGIS window, set its layers and zoom, then click **Capture current map view** for the selected frame. Repeat for the detail and locator maps. Initially, all frames inherit the current view when layers are available.
5. **Preview** hides planner overlays. Actual project layers render in the canvas asynchronously. **Guides** toggles the margin guide.
6. Enter a layout name and click **Create Layout**. A new print layout opens with real, editable map items. Each map keeps its captured extent, CRS, rotation, layers and styles. Existing layouts are preserved; duplicate names receive a numbered suffix.
7. Add your title, scale bars, legend or north arrows in QGIS. Export through the QGIS layout designer. Save the QGIS project to retain the print layout and planner configuration.

**QGIS steps** gives concise manual reproduction steps with the current frame measurements. Save/Load Plan writes or reads JSON plans. Captured layer IDs refer to the original QGIS project; recapture views when loading a plan into another project. Captured views retain layer references and style settings, not copies of layer datasets.

Changing page settings reapplies the chosen arrangement. Frame names and captured views are retained. Planner frame labels and size tags are editor overlays and are not added as labels to the resulting layout.

## Validation and limits

The package includes dependency-free geometry and saved-plan tests, plus a real-QGIS smoke test. The build environment has no QGIS/Qt installation, so native UI rendering and QGIS integration could not be executed there. Metadata declares the intended supported versions; this is not a claim of runtime testing on every QGIS version.

The geometry tests can also be run from the extracted ZIP folder with `python -m unittest discover -s layout_planner/tests -v`.

To run the included QGIS smoke test after installing, open Plugins → Python Console and enter:

```python
from layout_planner.selftest import run
run()
```

The smoke test uses a separate temporary in-memory QgsProject. It checks actual page size, map count, map geometry, layer locking and duplicate layout names without editing your open project.

No GIS datasets are included. Existing remote layers may still need their usual internet access. Rendering performance depends on your project layers; preview rasters are limited to about 700 pixels on the longest side. Missing/invalid layers must be recaptured before Create Layout.

## Source

`model.py`: geometry and JSON plans. `canvas.py`: native drag/resize editor. `dialog.py`: controls, per-frame capture and asynchronous previews. `layout_builder.py`: QGIS print layout creation. `plugin.py`: toolbar and lifecycle. No external dependencies.

Official API references: https://api.qgis.org/api/classQgsLayoutItemMap.html, https://api.qgis.org/api/classQgsLayoutItemPage.html, https://api.qgis.org/api/classQgsLayoutItem.html.

Author: Muhammad Naeem.
