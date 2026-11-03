# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Muhammad Naeem

"""QGIS plugin entry point. No optional dependencies are required."""


def classFactory(iface):
    from .plugin import LayoutPlannerPlugin
    return LayoutPlannerPlugin(iface)
