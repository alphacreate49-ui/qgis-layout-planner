"""Native Qt composition canvas with millimetre geometry and corner resizing."""
from copy import copy
from qgis.PyQt.QtCore import Qt, QPointF, QRectF, pyqtSignal
from qgis.PyQt.QtGui import QColor, QFont, QPainter, QPen
from qgis.PyQt.QtWidgets import QWidget


def enum(owner, group, name):
    return getattr(getattr(owner, group, owner), name)


ALIGN_CENTER = enum(Qt, "AlignmentFlag", "AlignCenter")
NO_PEN = enum(Qt, "PenStyle", "NoPen")


class PlannerCanvas(QWidget):
    frameSelected = pyqtSignal(int)
    frameChanged = pyqtSignal(int)
    editFinished = pyqtSignal(int)

    def __init__(self, plan, parent=None):
        super().__init__(parent)
        self.plan = plan
        self.selected = 1
        self.preview = False
        self.guides = True
        self.images = {}
        self._drag = None
        self._scale = 1.0
        self._page = QRectF()
        self.setMinimumSize(330, 300)
        self.setFocusPolicy(enum(Qt, "FocusPolicy", "StrongFocus"))
        self.setMouseTracking(True)
        self.setAccessibleName("Layout composition. Select and drag a map. Drag a corner to resize.")

    def page_rect(self):
        pw, ph = self.plan.page_size
        self._scale = max(.05, min((self.width() - 64) / pw, (self.height() - 64) / ph))
        width, height = pw * self._scale, ph * self._scale
        self._page = QRectF((self.width() - width) / 2, (self.height() - height) / 2, width, height)
        return self._page

    def frame_rect(self, frame):
        return QRectF(self._page.left() + frame.x * self._scale,
                      self._page.top() + frame.y * self._scale,
                      frame.width * self._scale, frame.height * self._scale)

    @staticmethod
    def corners(rect):
        return {"nw": rect.topLeft(), "ne": rect.topRight(), "sw": rect.bottomLeft(), "se": rect.bottomRight()}

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(enum(QPainter, "RenderHint", "Antialiasing"))
        painter.fillRect(self.rect(), QColor("#eef2f4"))
        painter.setPen(QPen(QColor("#d3dde0"), 1))
        for x in range(12, self.width(), 20):
            for y in range(12, self.height(), 20):
                painter.drawPoint(x, y)
        page = self.page_rect()
        painter.fillRect(page.translated(4, 7), QColor("#dce3e6"))
        painter.fillRect(page, QColor("white"))
        if self.guides and not self.preview:
            m = self.plan.margin * self._scale
            guide = QPen(QColor("#93bdb5"), 1, enum(Qt, "PenStyle", "DashLine"))
            painter.setPen(guide)
            painter.setBrush(enum(Qt, "BrushStyle", "NoBrush"))
            painter.drawRect(page.adjusted(m, m, -m, -m))
        ordered = sorted(self.plan.frames, key=lambda frame: frame.id == self.selected)
        font = QFont(self.font())
        font.setPointSize(8)
        painter.setFont(font)
        for frame in ordered:
            rect = self.frame_rect(frame)
            image = self.images.get(frame.id)
            painter.save()
            painter.setClipRect(rect)
            painter.fillRect(rect, QColor("#e5efea"))
            if image is not None and not image.isNull():
                painter.drawImage(rect, image)
            else:
                painter.setPen(QPen(QColor("#b9d1c5"), 1))
                for offset in range(-int(rect.height()), int(rect.width()) + 40, 28):
                    painter.drawLine(QPointF(rect.left() + offset, rect.bottom()),
                                     QPointF(rect.left() + offset + rect.height(), rect.top()))
                painter.setPen(QColor("#53776b"))
                painter.drawText(rect.adjusted(8, 28, -8, -18), int(ALIGN_CENTER), "Capture a map view" if not frame.view else "Map preview")
            painter.restore()
            painter.setBrush(enum(Qt, "BrushStyle", "NoBrush"))
            selected = frame.id == self.selected and not self.preview
            if selected or self.plan.outline:
                painter.setPen(QPen(QColor("#0d9e77" if selected else "#6d8b81"), 2 if selected else 1))
                painter.drawRect(rect)
            if not self.preview:
                caption = f"{frame.id:02d}  {frame.name}"
                label_width = min(rect.width() - 10, painter.fontMetrics().horizontalAdvance(caption) + 16)
                label = QRectF(rect.left() + 5, rect.top() + 5, max(10, label_width), 22)
                painter.setPen(NO_PEN)
                painter.setBrush(QColor("#f9fcfa"))
                painter.drawRoundedRect(label, 3, 3)
                painter.setPen(QColor("#35594c"))
                text = painter.fontMetrics().elidedText(caption, enum(Qt, "TextElideMode", "ElideRight"), max(5, int(label.width()) - 10))
                painter.drawText(label, int(ALIGN_CENTER), text)
                painter.setPen(QColor("#345d4f"))
                painter.drawText(rect.adjusted(5, 27, -5, -5), int(enum(Qt, "AlignmentFlag", "AlignBottom") | enum(Qt, "AlignmentFlag", "AlignRight")), f"{frame.width:.1f} × {frame.height:.1f}")
            if selected:
                for corner in self.corners(rect).values():
                    painter.setPen(QPen(QColor("#0b936c"), 1.5))
                    painter.setBrush(QColor("white"))
                    painter.drawRect(QRectF(corner.x() - 4, corner.y() - 4, 8, 8))
        painter.setPen(QColor("#748992"))
        pw, ph = self.plan.page_size
        painter.drawText(QRectF(page.left(), page.top() - 24, page.width(), 18), int(ALIGN_CENTER), f"{pw:g} × {ph:g} mm")
        painter.end()

    @staticmethod
    def event_point(event):
        return event.position() if hasattr(event, "position") else QPointF(event.pos())

    def handle_at(self, point):
        frame = next((f for f in self.plan.frames if f.id == self.selected), None)
        if frame:
            for name, corner in self.corners(self.frame_rect(frame)).items():
                if abs(point.x() - corner.x()) <= 8 and abs(point.y() - corner.y()) <= 8:
                    return frame, name
        for candidate in sorted(self.plan.frames, key=lambda f: f.id == self.selected, reverse=True):
            if self.frame_rect(candidate).contains(point):
                return candidate, "move"
        return None, None

    def mousePressEvent(self, event):
        if self.preview or event.button() != enum(Qt, "MouseButton", "LeftButton"):
            return super().mousePressEvent(event)
        self.page_rect()
        point = self.event_point(event)
        frame, handle = self.handle_at(point)
        if frame is None:
            return
        self.setFocus()
        self.selected = frame.id
        self.frameSelected.emit(frame.id)
        self._drag = (frame, copy(frame), handle, point)
        self.update()

    def mouseMoveEvent(self, event):
        point = self.event_point(event)
        if self.preview:
            return
        if self._drag:
            frame, original, handle, start = self._drag
            dx, dy = (point.x() - start.x()) / self._scale, (point.y() - start.y()) / self._scale
            if handle == "move":
                frame.x, frame.y = original.x + dx, original.y + dy
                self.plan.constrain(frame)
            else:
                self.plan.resize(frame, original, handle, dx, dy)
            self.frameChanged.emit(frame.id)
            self.update()
        else:
            _, handle = self.handle_at(point)
            cursor = "ArrowCursor" if not handle else "SizeAllCursor" if handle == "move" else "SizeFDiagCursor" if handle in ("nw", "se") else "SizeBDiagCursor"
            self.setCursor(enum(Qt, "CursorShape", cursor))

    def mouseReleaseEvent(self, event):
        if self._drag:
            frame = self._drag[0]
            self._drag = None
            self.editFinished.emit(frame.id)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if self.preview:
            return super().keyPressEvent(event)
        directions = {enum(Qt, "Key", "Key_Left"): (-1, 0), enum(Qt, "Key", "Key_Right"): (1, 0),
                      enum(Qt, "Key", "Key_Up"): (0, -1), enum(Qt, "Key", "Key_Down"): (0, 1)}
        if event.key() not in directions:
            return super().keyPressEvent(event)
        frame = next(f for f in self.plan.frames if f.id == self.selected)
        step = 5 if event.modifiers() & enum(Qt, "KeyboardModifier", "ShiftModifier") else .5
        dx, dy = directions[event.key()]
        frame.x += dx * step
        frame.y += dy * step
        self.plan.constrain(frame)
        self.frameChanged.emit(frame.id)
        self.update()
        event.accept()
