# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Muhammad Naeem

"""Run inside QGIS's Python Console. Uses an isolated project, not user data."""


def _require(condition, message):
    """Keep smoke-test validation active even with optimized Python."""
    if not condition:
        raise AssertionError(message)


def run():
    from qgis.core import QgsProject, QgsVectorLayer, QgsLayoutItemMap
    from .layout_builder import build_layout
    from .model import Plan

    project = QgsProject()
    layer = QgsVectorLayer("Point?crs=EPSG:4326", "Layout Planner test", "memory")
    _require(layer.isValid(), "Memory layer creation failed")
    project.addMapLayer(layer)
    checks = 0
    for count in (2, 3):
        for orientation in ("landscape", "portrait"):
            plan = Plan(count=count, orientation=orientation)
            plan.arrange()
            for frame in plan.frames:
                frame.view = {"extent": [70, 28, 75, 33], "crs": layer.crs().toWkt(), "layers": [layer.id()]}
            layout = build_layout(plan, project)
            maps = [item for item in layout.items() if isinstance(item, QgsLayoutItemMap)]
            _require(len(maps) == count, f"Expected {count} maps")
            page_size = layout.pageCollection().page(0).pageSize()
            pw, ph = plan.page_size
            _require(abs(page_size.width() - pw) < .01 and abs(page_size.height() - ph) < .01,
                     "Created page dimensions do not match the plan")
            for frame in plan.frames:
                item = next(m for m in maps if m.id().startswith(f"map_{frame.id}_"))
                pos, size = item.positionWithUnits(), item.sizeWithUnits()
                _require(abs(pos.x() - frame.x) < .01 and abs(pos.y() - frame.y) < .01,
                         f"Map {frame.id} position does not match the plan")
                _require(abs(size.width() - frame.width) < .01 and abs(size.height() - frame.height) < .01,
                         f"Map {frame.id} dimensions do not match the plan")
                _require(item.keepLayerSet() and item.keepLayerStyles(),
                         f"Map {frame.id} did not retain layer/style locking")
                _require(bool(item.layers()) and item.layers()[0].id() == layer.id(),
                         f"Map {frame.id} did not retain the captured layer")
                checks += 1
            duplicate = build_layout(plan, project)
            _require(duplicate.name() != layout.name(), "Duplicate names must be made unique")
            project.layoutManager().removeLayout(duplicate)
            project.layoutManager().removeLayout(layout)
    project.clear()
    message = f"Layout Planner QGIS smoke test: PASS ({checks} map frames checked)."
    print(message)
    return message
