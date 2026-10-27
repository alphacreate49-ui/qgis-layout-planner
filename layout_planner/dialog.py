"""Modern native QGIS layout planner dialog, compatible with Qt 5 and Qt 6."""
from copy import deepcopy
from pathlib import Path

from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog,
    QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
    QSplitter, QVBoxLayout, QWidget,
)
from qgis.core import QgsMapRendererParallelJob, QgsProject
from .canvas import PlannerCanvas, enum
from .layout_builder import build_layout, capture_canvas, preview_settings
from .model import PAGE_SIZES, Plan
from .theme import STYLE


class PlannerDialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.project = QgsProject.instance()
        self.jobs = {}
        self._closing = False
        self._syncing = False
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self.refresh_selected_preview)
        saved, _ = self.project.readEntry("LayoutPlanner", "plan", "")
        try:
            self.plan = Plan.from_json(saved) if saved else Plan()
        except (ValueError, TypeError, KeyError):
            self.plan = Plan()
        if not self.plan.frames:
            self.plan.arrange()
        self.selected = 1
        self.setObjectName("LayoutPlannerDialog")
        self.setWindowTitle("Layout Planner · QGIS")
        self.setWindowIcon(QIcon(str(Path(__file__).with_name("icon.svg"))))
        self.setModal(False)
        self.setMinimumSize(1000, 590)
        screen = QApplication.primaryScreen()
        area = screen.availableGeometry() if screen else None
        self.resize(min(1260, area.width() - 70) if area else 1200,
                    min(800, area.height() - 70) if area else 760)
        self.setStyleSheet(STYLE)
        self._build_ui()
        self.capture_missing_views()
        self.sync()
        QTimer.singleShot(0, self.refresh_all_previews)

    @staticmethod
    def label(text, role=None, wrap=False):
        widget = QLabel(text)
        if role:
            widget.setProperty("role", role)
        widget.setWordWrap(wrap)
        return widget

    @staticmethod
    def button(text, callback, name=None):
        widget = QPushButton(text)
        if name:
            widget.setObjectName(name)
        widget.clicked.connect(callback)
        return widget

    @staticmethod
    def separator(layout):
        line = QFrame()
        line.setProperty("role", "separator")
        line.setFixedHeight(1)
        layout.addWidget(line)

    @staticmethod
    def scroll_panel(name, width):
        panel = QFrame()
        panel.setObjectName(name)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 20, 18, 18)
        layout.setSpacing(12)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(panel)
        scroll.setMinimumWidth(width)
        return scroll, layout

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        header = QFrame()
        header.setObjectName("Header")
        top = QHBoxLayout(header)
        top.setContentsMargins(20, 14, 20, 14)
        logo = QLabel()
        logo.setPixmap(self.windowIcon().pixmap(36, 36))
        top.addWidget(logo)
        brand = QVBoxLayout()
        brand.setSpacing(1)
        brand.addWidget(self.label("Layout Planner", "title"))
        brand.addWidget(self.label("QGIS PRINT LAYOUT TOOL", "subtitle"))
        top.addLayout(brand)
        top.addStretch()
        top.addWidget(self.label("LOCAL WORKSPACE", "subtitle"))
        top.addSpacing(15)
        top.addWidget(self.button("QGIS steps", self.show_steps, "HeaderSecondary"))
        top.addWidget(self.button("Create Layout  →", self.create_layout, "Primary"))
        root.addWidget(header)

        splitter = QSplitter(enum(Qt, "Orientation", "Horizontal"))
        self.left_panel, left = self.scroll_panel("Sidebar", 235)
        left.addWidget(self.label("PAGE SETUP", "section"))
        left.addWidget(self.label("Page size"))
        self.size_combo = QComboBox()
        self.size_combo.addItems(list(PAGE_SIZES))
        left.addWidget(self.size_combo)
        left.addWidget(self.label("Orientation"))
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItem("Landscape", "landscape")
        self.orientation_combo.addItem("Portrait", "portrait")
        left.addWidget(self.orientation_combo)
        self.separator(left)
        left.addWidget(self.label("ARRANGEMENT", "section"))
        row = QHBoxLayout()
        row.addWidget(self.label("Map frames"))
        self.count_combo = QComboBox()
        self.count_combo.addItem("2 maps", 2)
        self.count_combo.addItem("3 maps", 3)
        row.addWidget(self.count_combo)
        left.addLayout(row)
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("▥   Main map + details", "feature")
        self.preset_combo.addItem("▥   Side by side", "columns")
        self.preset_combo.addItem("☰   Stacked maps", "rows")
        left.addWidget(self.preset_combo)
        spacing = QGridLayout()
        self.margin_spin = self.spin(0, 100)
        self.gap_spin = self.spin(0, 30)
        for i, (label, spin) in enumerate((("Margin", self.margin_spin), ("Spacing", self.gap_spin))):
            spacing.addWidget(self.label(label), i, 0)
            spin.setSuffix(" mm")
            spacing.addWidget(spin, i, 1)
        left.addLayout(spacing)
        left.addWidget(self.button("Reapply arrangement", self.reflow))
        left.addWidget(self.label("Page settings reflow the frames.", "muted", True))
        self.separator(left)
        left.addWidget(self.label("MAP FRAMES", "section"))
        self.frame_list = QListWidget()
        self.frame_list.setMinimumHeight(150)
        self.frame_list.setMaximumHeight(210)
        self.frame_list.currentRowChanged.connect(self.select_row)
        left.addWidget(self.frame_list)
        left.addStretch()
        files = QHBoxLayout()
        files.addWidget(self.button("Save plan", self.save_plan))
        files.addWidget(self.button("Load plan", self.load_plan))
        left.addLayout(files)
        splitter.addWidget(self.left_panel)

        center = QWidget()
        middle = QVBoxLayout(center)
        middle.setContentsMargins(0, 0, 0, 0)
        middle.setSpacing(0)
        bar = QFrame()
        bar.setObjectName("CanvasBar")
        tools = QHBoxLayout(bar)
        tools.setContentsMargins(17, 9, 17, 9)
        self.page_info = self.label("", "muted")
        tools.addWidget(self.page_info)
        tools.addStretch()
        self.guides_button = self.button("Guides", self.toggle_guides)
        self.guides_button.setCheckable(True)
        self.guides_button.setChecked(True)
        tools.addWidget(self.guides_button)
        self.preview_button = self.button("Preview", self.toggle_preview)
        self.preview_button.setCheckable(True)
        tools.addWidget(self.preview_button)
        middle.addWidget(bar)
        self.canvas = PlannerCanvas(self.plan)
        self.canvas.frameSelected.connect(self.select_frame)
        self.canvas.frameChanged.connect(self.canvas_edited)
        self.canvas.editFinished.connect(self.canvas_edit_finished)
        middle.addWidget(self.canvas, 1)
        self.status = self.label("")
        self.status.setObjectName("Status")
        self.status.setWordWrap(True)
        self.status.setContentsMargins(16, 10, 16, 10)
        middle.addWidget(self.status)
        splitter.addWidget(center)

        self.right_panel, right = self.scroll_panel("Inspector", 245)
        right.addWidget(self.label("FRAME PROPERTIES", "section"))
        self.selected_label = self.label("", "title")
        self.selected_label.setWordWrap(True)
        right.addWidget(self.selected_label)
        right.addWidget(self.label("Frame name"))
        self.name_edit = QLineEdit()
        self.name_edit.setMaxLength(60)
        self.name_edit.editingFinished.connect(self.name_changed)
        right.addWidget(self.name_edit)
        properties = QGridLayout()
        self.geometry_spins = {}
        for i, (key, label) in enumerate((("x", "X position"), ("y", "Y position"), ("width", "Width"), ("height", "Height"))):
            column, row = i % 2, (i // 2) * 2
            spin = self.spin(0, 1000)
            spin.setSuffix(" mm")
            spin.editingFinished.connect(self.geometry_changed)
            properties.addWidget(self.label(label, "muted"), row, column)
            properties.addWidget(spin, row + 1, column)
            self.geometry_spins[key] = spin
        right.addLayout(properties)
        right.addWidget(self.label("Origin: page top-left corner.", "muted"))
        self.separator(right)
        right.addWidget(self.label("MAP CONTENT", "section"))
        right.addWidget(self.label("Set layers and zoom in the main QGIS window, then capture them for this frame.", "muted", True))
        right.addWidget(self.button("Capture current map view", self.capture_selected))
        self.view_info = self.label("", "hint", True)
        right.addWidget(self.view_info)
        right.addWidget(self.button("Refresh map previews", self.refresh_all_previews, "Link"))
        self.separator(right)
        self.outline_check = QCheckBox("Map frame outlines")
        self.outline_check.toggled.connect(self.outline_changed)
        right.addWidget(self.outline_check)
        right.addWidget(self.label("Drag a frame to move it. Drag a corner to resize. Arrow keys: 0.5 mm; Shift + arrows: 5 mm.", "muted", True))
        right.addStretch()
        right.addWidget(self.label("PRINT LAYOUT", "section"))
        self.layout_name = QLineEdit(self.plan.name)
        self.layout_name.setMaxLength(100)
        self.layout_name.setPlaceholderText("Layout name")
        self.layout_name.editingFinished.connect(self.layout_name_changed)
        right.addWidget(self.layout_name)
        right.addWidget(self.button("Reset arrangement", self.reset, "Link"))
        splitter.addWidget(self.right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([245, 730, 260])
        root.addWidget(splitter, 1)
        footer = QFrame()
        footer.setObjectName("StatusBar")
        foot = QHBoxLayout(footer)
        foot.setContentsMargins(18, 7, 18, 7)
        foot.addWidget(self.label("Editable QGIS map items · Millimetres · No extra packages", "muted"))
        foot.addStretch()
        foot.addWidget(self.label("Layout Planner 1.0", "muted"))
        root.addWidget(footer)

        for combo in (self.size_combo, self.orientation_combo, self.count_combo, self.preset_combo):
            combo.currentIndexChanged.connect(self.settings_changed)
        for spin in (self.margin_spin, self.gap_spin):
            spin.editingFinished.connect(self.settings_changed)

    @staticmethod
    def spin(minimum, maximum):
        spin = QDoubleSpinBox()
        spin.setDecimals(1)
        spin.setRange(minimum, maximum)
        spin.setSingleStep(.5)
        spin.setKeyboardTracking(False)
        return spin

    def current_frame(self):
        return next((f for f in self.plan.frames if f.id == self.selected), self.plan.frames[0])

    def sync(self, rebuild_list=True):
        self._syncing = True
        self.size_combo.setCurrentText(self.plan.size)
        self.orientation_combo.setCurrentIndex(self.orientation_combo.findData(self.plan.orientation))
        self.count_combo.setCurrentIndex(self.count_combo.findData(self.plan.count))
        self.preset_combo.setCurrentIndex(self.preset_combo.findData(self.plan.preset))
        self.margin_spin.setMaximum(self.plan.max_margin)
        self.margin_spin.setValue(self.plan.margin)
        self.gap_spin.setMaximum(self.plan.max_gap)
        self.gap_spin.setValue(self.plan.gap)
        self.outline_check.setChecked(self.plan.outline)
        self.layout_name.setText(self.plan.name)
        if rebuild_list:
            self.frame_list.clear()
            for frame in self.plan.frames:
                item = QListWidgetItem(f"{frame.id:02d}   {frame.name}\n      {frame.width:.1f} × {frame.height:.1f} mm")
                self.frame_list.addItem(item)
            self.frame_list.setCurrentRow(self.selected - 1)
        frame = self.current_frame()
        self.selected_label.setText(f"{frame.id:02d}  {frame.name}")
        self.name_edit.setText(frame.name)
        pw, ph = self.plan.page_size
        bounds = {"x": (self.plan.margin, pw - self.plan.margin - frame.width),
                  "y": (self.plan.margin, ph - self.plan.margin - frame.height),
                  "width": (20, pw - 2 * self.plan.margin), "height": (20, ph - 2 * self.plan.margin)}
        for key, spin in self.geometry_spins.items():
            spin.setRange(*bounds[key])
            spin.setValue(getattr(frame, key))
        layers = frame.view.get("layers", [])
        self.view_info.setText(f"View captured · {len(layers)} layer(s)\nCreate Layout keeps these layers and styles." if layers else "No view captured. Enable QGIS layers and capture a view.")
        self.page_info.setText(f"{self.plan.size} · {self.plan.orientation.title()}   /   {pw:g} × {ph:g} mm")
        self.canvas.plan = self.plan
        self.canvas.selected = self.selected
        self.canvas.update()
        self.update_status()
        self._syncing = False

    def update_status(self):
        collisions = self.plan.overlaps()
        missing = sum(not f.view.get("layers") for f in self.plan.frames)
        message = "Overlap: " + "; ".join(f"map {a} & {b}" for a, b in collisions) if collisions else f"✓ {self.plan.count} frames inside margins · No overlaps"
        if missing:
            message += f" · Capture {missing} map view(s)"
        self.status.setText(message)
        self.status.setProperty("warning", bool(collisions or missing))
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def settings_changed(self, *args):
        if self._syncing:
            return
        self.plan.size = self.size_combo.currentText()
        self.plan.orientation = self.orientation_combo.currentData()
        self.plan.count = self.count_combo.currentData()
        self.plan.preset = self.preset_combo.currentData()
        self.plan.margin = self.margin_spin.value()
        self.plan.gap = self.gap_spin.value()
        self.reflow()

    def reflow(self):
        self.plan.arrange()
        self.selected = min(self.selected, self.plan.count)
        self.capture_missing_views()
        self.sync()
        self.refresh_all_previews()

    def select_row(self, row):
        if not self._syncing and row >= 0:
            self.select_frame(row + 1)

    def select_frame(self, frame_id):
        self.selected = frame_id
        self.sync()

    def name_changed(self):
        if not self._syncing:
            frame = self.current_frame()
            frame.name = self.name_edit.text().strip() or f"Map {frame.id}"
            self.sync()

    def layout_name_changed(self):
        self.plan.name = self.layout_name.text().strip() or "Multi-map layout"

    def geometry_changed(self):
        if self._syncing:
            return
        frame = self.current_frame()
        for key, spin in self.geometry_spins.items():
            setattr(frame, key, spin.value())
        self.plan.constrain(frame)
        self.sync()
        self._preview_timer.start(250)

    def outline_changed(self, enabled):
        if not self._syncing:
            self.plan.outline = bool(enabled)
            self.canvas.update()

    def canvas_edited(self, frame_id):
        self.selected = frame_id
        self.sync()

    def canvas_edit_finished(self, frame_id):
        self.selected = frame_id
        self.sync()
        self.refresh_selected_preview()

    def capture_missing_views(self):
        if not self.iface.mapCanvas().layers():
            return
        try:
            snapshot = capture_canvas(self.iface.mapCanvas())
        except ValueError:
            return
        for frame in self.plan.frames:
            if not frame.view:
                frame.view = deepcopy(snapshot)

    def capture_selected(self):
        try:
            snapshot = capture_canvas(self.iface.mapCanvas())
            if not snapshot["layers"]:
                raise ValueError("Enable at least one layer in the main QGIS window first.")
            self.current_frame().view = snapshot
            self.sync()
            self.refresh_selected_preview()
        except Exception as error:
            self.notify(str(error))

    def refresh_selected_preview(self):
        if not self._closing:
            self.refresh_preview(self.current_frame())

    def refresh_all_previews(self):
        if self._closing:
            return
        self.cancel_jobs()
        self.canvas.images.clear()
        for frame in self.plan.frames:
            self.refresh_preview(frame)
        self.canvas.update()

    def refresh_preview(self, frame):
        old = self.jobs.pop(frame.id, None)
        if old:
            old.cancel()
            old.deleteLater()
        self.canvas.images.pop(frame.id, None)
        if not frame.view:
            return
        try:
            job = QgsMapRendererParallelJob(preview_settings(frame, self.project))
        except (ValueError, TypeError, RuntimeError):
            self.canvas.update()
            return
        self.jobs[frame.id] = job
        job.finished.connect(lambda frame_id=frame.id, render_job=job: self.preview_finished(frame_id, render_job))
        job.start()

    def preview_finished(self, frame_id, job):
        if self.jobs.get(frame_id) is not job:
            return
        self.jobs.pop(frame_id, None)
        if not self._closing:
            image = job.renderedImage()
            if not image.isNull():
                self.canvas.images[frame_id] = image
            self.canvas.update()
            errors = job.errors()
            if errors:
                self.status.setText(f"Map {frame_id} preview: {errors[0].message}")
        job.deleteLater()

    def toggle_guides(self, checked):
        self.canvas.guides = checked
        self.canvas.update()

    def toggle_preview(self, checked):
        self.canvas.preview = checked
        self.preview_button.setText("Edit layout" if checked else "Preview")
        self.left_panel.setEnabled(not checked)
        self.right_panel.setEnabled(not checked)
        self.guides_button.setEnabled(not checked)
        self.canvas.update()

    def show_steps(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("QGIS steps · Layout Planner")
        dialog.resize(720, 550)
        layout = QVBoxLayout(dialog)
        layout.addWidget(self.label("Reproduce this arrangement", "title"))
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText(self.plan.steps())
        layout.addWidget(text)
        actions = QHBoxLayout()
        copy_button = self.button("Copy steps", lambda: QApplication.clipboard().setText(text.toPlainText()))
        actions.addWidget(copy_button)
        actions.addStretch()
        actions.addWidget(self.button("Close", dialog.accept))
        layout.addLayout(actions)
        dialog.exec()

    def notify(self, message, warning=True):
        if warning:
            QMessageBox.warning(self, "Layout Planner", message)
        else:
            QMessageBox.information(self, "Layout Planner", message)

    def create_layout(self):
        self.layout_name_changed()
        try:
            layout = build_layout(self.plan, self.project)
        except Exception as error:
            self.notify(str(error))
            return
        self.persist()
        self.hide()
        try:
            self.iface.openLayoutDesigner(layout)
        except Exception as error:
            self.show()
            self.notify(f"Layout '{layout.name()}' was created. Open it from Project → Layouts.\n\n{error}")

    def save_plan(self):
        self.layout_name_changed()
        path, _ = QFileDialog.getSaveFileName(self, "Save layout plan", "layout_plan.json", "Layout plan (*.json)")
        if path:
            try:
                if not path.lower().endswith(".json"):
                    path += ".json"
                Path(path).write_text(self.plan.to_json(), encoding="utf-8")
            except (OSError, ValueError) as error:
                self.notify(str(error))

    def load_plan(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load layout plan", "", "Layout plan (*.json)")
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
            plan = Plan.from_json(text)
        except (OSError, ValueError, TypeError, KeyError) as error:
            self.notify(f"Could not load this plan: {error}")
            return
        self.cancel_jobs()
        self.plan = plan
        self.selected = 1
        self.capture_missing_views()
        self.sync()
        self.refresh_all_previews()

    def reset(self):
        self.cancel_jobs()
        self.plan = Plan()
        self.plan.arrange()
        self.selected = 1
        self.capture_missing_views()
        self.sync()
        self.refresh_all_previews()

    def persist(self):
        if not self._closing:
            self.project.writeEntry("LayoutPlanner", "plan", self.plan.to_json())

    def cancel_jobs(self):
        self._preview_timer.stop()
        jobs, self.jobs = self.jobs, {}
        for job in jobs.values():
            job.cancel()
            job.deleteLater()

    def shutdown(self, save=True):
        if save:
            self.persist()
        self._closing = True
        self.cancel_jobs()

    def closeEvent(self, event):
        self.shutdown()
        super().closeEvent(event)

    def reject(self):
        self.shutdown()
        super().reject()
