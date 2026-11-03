# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Muhammad Naeem

"""QGIS plugin lifecycle and toolbar integration."""
from pathlib import Path
from qgis.PyQt.QtGui import QIcon
try:
    from qgis.PyQt.QtGui import QAction
except ImportError:
    from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsProject


class LayoutPlannerPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        self.action = QAction(QIcon(str(Path(__file__).with_name("icon.svg"))), "Layout Planner", self.iface.mainWindow())
        self.action.setToolTip("Arrange multiple maps on one QGIS print layout")
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Layout Planner", self.action)
        QgsProject.instance().cleared.connect(self.project_cleared)

    def run(self):
        from .dialog import PlannerDialog
        if self.dialog is None or self.dialog._closing:
            if self.dialog is not None:
                self.dialog.deleteLater()
            self.dialog = PlannerDialog(self.iface)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def project_cleared(self):
        if self.dialog is not None:
            self.dialog.shutdown(save=False)
            self.dialog.close()
            self.dialog.deleteLater()
            self.dialog = None

    def unload(self):
        try:
            QgsProject.instance().cleared.disconnect(self.project_cleared)
        except (TypeError, RuntimeError):
            pass
        if self.dialog is not None:
            self.dialog.shutdown()
            self.dialog.close()
            self.dialog.deleteLater()
            self.dialog = None
        if self.action is not None:
            self.iface.removePluginMenu("&Layout Planner", self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None
