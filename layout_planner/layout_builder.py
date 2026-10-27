"""QGIS integration: map views, background preview jobs and real print layouts."""
import math
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsCoordinateReferenceSystem, QgsLayoutItemMap, QgsLayoutItem,
    QgsLayoutMeasurement, QgsLayoutPoint, QgsLayoutSize,
    QgsMapLayerStyle, QgsMapSettings, QgsPrintLayout, QgsRectangle,
)


def capture_canvas(canvas):
    extent = canvas.extent()
    if extent.isEmpty() or not all(math.isfinite(v) for v in (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum())):
        raise ValueError("Zoom to a valid area in the QGIS map canvas first.")
    styles = {}
    layers = canvas.layers()
    for layer in layers:
        style = QgsMapLayerStyle()
        style.readFromLayer(layer)
        styles[layer.id()] = style.xmlData()
    return {"extent": [extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()],
            "crs": canvas.mapSettings().destinationCrs().toWkt(),
            "layers": [layer.id() for layer in layers], "styles": styles,
            "rotation": canvas.rotation()}


def resolve_view(view, project):
    values = view.get("extent", [])
    if not isinstance(values, (list, tuple)) or len(values) != 4 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
        raise ValueError("This frame has no valid captured extent. Capture its current map view.")
    extent = QgsRectangle(*values)
    if extent.isEmpty():
        raise ValueError("Captured map extent is empty. Capture a new map view.")
    crs = QgsCoordinateReferenceSystem(view.get("crs", ""))
    if not crs.isValid():
        raise ValueError("Captured map CRS is invalid. Capture a new map view.")
    layer_ids = view.get("layers", [])
    if not isinstance(layer_ids, list):
        raise ValueError("Invalid captured layers. Capture this map view again.")
    layers = [project.mapLayer(layer_id) for layer_id in layer_ids if isinstance(layer_id, str)]
    if any(layer is None or not layer.isValid() for layer in layers):
        raise ValueError("A captured layer is missing or invalid. Reload it or capture this view again.")
    if not layers:
        raise ValueError("No visible layers were captured. Enable layers and capture this map view.")
    return extent, crs, layers


def preview_settings(frame, project):
    extent, crs, layers = resolve_view(frame.view, project)
    settings = QgsMapSettings()
    settings.setLayers(layers)
    settings.setDestinationCrs(crs)
    settings.setTransformContext(project.transformContext())
    settings.setBackgroundColor(QColor("#ffffff"))
    longest = max(frame.width, frame.height)
    settings.setOutputSize(QSize(max(80, round(700 * frame.width / longest)), max(80, round(700 * frame.height / longest))))
    settings.setOutputDpi(96)
    settings.setRotation(float(frame.view.get("rotation", 0)))
    settings.setExtent(extent)
    settings.setLayerStyleOverrides(frame.view.get("styles", {}))
    return settings


def build_layout(plan, project):
    """Validate before modifying the project; return a newly registered layout."""
    views = [resolve_view(frame.view, project) for frame in plan.frames]
    manager = project.layoutManager()
    base = plan.name.strip() or "Multi-map layout"
    name, index = base, 2
    while manager.layoutByName(name) is not None:
        name = f"{base} ({index})"
        index += 1
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(name)
    pw, ph = plan.page_size
    layout.pageCollection().page(0).setPageSize(QgsLayoutSize(pw, ph))
    layout.renderContext().setDpi(300)
    reference = getattr(getattr(QgsLayoutItem, "ReferencePoint", QgsLayoutItem), "UpperLeft")
    for frame, (extent, crs, layers) in zip(plan.frames, views):
        item = QgsLayoutItemMap(layout)
        layout.addLayoutItem(item)
        item.setId(f"map_{frame.id}_{frame.name}")
        item.setReferencePoint(reference)
        item.attemptResize(QgsLayoutSize(frame.width, frame.height))
        item.attemptMove(QgsLayoutPoint(frame.x, frame.y))
        item.setCrs(crs)
        item.setLayers(layers)
        item.setKeepLayerSet(True)
        item.setLayerStyleOverrides(frame.view.get("styles", {}))
        item.setKeepLayerStyles(True)
        item.setMapRotation(float(frame.view.get("rotation", 0)))
        item.zoomToExtent(extent)
        item.setFrameEnabled(plan.outline)
        item.setFrameStrokeColor(QColor("#334b46"))
        item.setFrameStrokeWidth(QgsLayoutMeasurement(.25))
        item.setBackgroundEnabled(True)
        item.setBackgroundColor(QColor("white"))
    layout.refresh()
    if not manager.addLayout(layout):
        raise RuntimeError("QGIS could not add the new print layout.")
    project.setDirty(True)
    return layout
