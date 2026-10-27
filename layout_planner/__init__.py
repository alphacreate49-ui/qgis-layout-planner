"""QGIS plugin entry point. No optional dependencies are required."""


def classFactory(iface):
    from .plugin import LayoutPlannerPlugin
    return LayoutPlannerPlugin(iface)
