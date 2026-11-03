# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Muhammad Naeem

"""Dependency-free layout geometry. Every coordinate is in page millimetres."""
from dataclasses import asdict, dataclass, field
from copy import deepcopy
import json
import math

PAGE_SIZES = {"A5": (148.0, 210.0), "A4": (210.0, 297.0),
              "A3": (297.0, 420.0), "Letter": (215.9, 279.4),
              "Legal": (215.9, 355.6)}
MIN_SIZE = 20.0


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def number(value, fallback=0.0):
    try:
        value = float(value)
        return value if math.isfinite(value) else fallback
    except (ValueError, TypeError):
        return fallback


@dataclass
class MapFrame:
    id: int
    name: str
    x: float
    y: float
    width: float
    height: float
    view: dict = field(default_factory=dict)

    @property
    def right(self):
        return self.x + self.width

    @property
    def bottom(self):
        return self.y + self.height


@dataclass
class Plan:
    size: str = "A4"
    orientation: str = "landscape"
    count: int = 3
    preset: str = "feature"
    margin: float = 12.0
    gap: float = 6.0
    name: str = "Multi-map layout"
    outline: bool = True
    frames: list = field(default_factory=list)

    @property
    def page_size(self):
        width, height = PAGE_SIZES.get(self.size, PAGE_SIZES["A4"])
        return (height, width) if self.orientation == "landscape" else (width, height)

    @property
    def max_margin(self):
        return math.floor((min(self.page_size) - 80) / 2)

    @property
    def max_gap(self):
        pw, ph = self.page_size
        width, height = pw - 2 * self.margin, ph - 2 * self.margin
        if self.preset == "columns":
            maximum = (width - self.count * MIN_SIZE) / (self.count - 1)
        elif self.preset == "rows":
            maximum = (height - self.count * MIN_SIZE) / (self.count - 1)
        else:
            maximum = min(width - 60, height - 40 if self.count == 3 else 30)
        return max(0, min(30, math.floor(maximum)))

    def normalize(self):
        self.size = self.size if self.size in PAGE_SIZES else "A4"
        self.orientation = self.orientation if self.orientation in ("portrait", "landscape") else "landscape"
        self.count = 2 if self.count == 2 else 3
        self.preset = self.preset if self.preset in ("feature", "rows", "columns") else "feature"
        self.margin = clamp(number(self.margin, 12), 0, self.max_margin)
        self.gap = clamp(number(self.gap, 6), 0, self.max_gap)
        self.name = str(self.name).strip()[:100] or "Multi-map layout"

    def arrange(self):
        self.normalize()
        old = {frame.id: frame for frame in self.frames}
        pw, ph = self.page_size
        m, g, n = self.margin, self.gap, self.count
        width, height = pw - 2 * m, ph - 2 * m
        boxes = []
        if self.preset == "columns":
            fw = (width - g * (n - 1)) / n
            boxes = [(m + i * (fw + g), m, fw, height) for i in range(n)]
        elif self.preset == "rows":
            fh = (height - g * (n - 1)) / n
            boxes = [(m, m + i * (fh + g), width, fh) for i in range(n)]
        else:
            main = (width - g) * .66
            side = width - g - main
            sh = (height - g * (n - 2)) / (n - 1)
            boxes = [(m, m, main, height)]
            boxes += [(m + main + g, m + i * (sh + g), side, sh) for i in range(n - 1)]
        names = ["Main map", "Detail map", "Locator map"]
        self.frames = [MapFrame(i + 1, old[i + 1].name if i + 1 in old else names[i],
                                *box, deepcopy(old[i + 1].view) if i + 1 in old else {})
                       for i, box in enumerate(boxes)]

    def constrain(self, frame):
        pw, ph = self.page_size
        m = self.margin
        frame.width = clamp(number(frame.width, MIN_SIZE), MIN_SIZE, pw - 2 * m)
        frame.height = clamp(number(frame.height, MIN_SIZE), MIN_SIZE, ph - 2 * m)
        frame.x = clamp(number(frame.x, m), m, pw - m - frame.width)
        frame.y = clamp(number(frame.y, m), m, ph - m - frame.height)

    def resize(self, frame, original, handle, dx, dy):
        pw, ph = self.page_size
        x, y, right, bottom = original.x, original.y, original.right, original.bottom
        if "e" in handle:
            right = clamp(right + dx, x + MIN_SIZE, pw - self.margin)
        if "s" in handle:
            bottom = clamp(bottom + dy, y + MIN_SIZE, ph - self.margin)
        if "w" in handle:
            x = clamp(x + dx, self.margin, right - MIN_SIZE)
        if "n" in handle:
            y = clamp(y + dy, self.margin, bottom - MIN_SIZE)
        frame.x, frame.y, frame.width, frame.height = x, y, right - x, bottom - y

    def overlaps(self):
        collisions = []
        for i, a in enumerate(self.frames):
            for b in self.frames[i + 1:]:
                if min(a.right, b.right) - max(a.x, b.x) > .05 and min(a.bottom, b.bottom) - max(a.y, b.y) > .05:
                    collisions.append((a.id, b.id))
        return collisions

    def to_json(self):
        return json.dumps(asdict(self), ensure_ascii=False, allow_nan=False)

    @classmethod
    def from_json(cls, text):
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("Plan must be a JSON object.")
        plan = cls(**{key: data[key] for key in ("size", "orientation", "count", "preset", "margin", "gap", "name", "outline") if key in data})
        plan.normalize()
        raw = data.get("frames", [])
        if not isinstance(raw, list) or len(raw) != plan.count:
            plan.arrange()
            return plan
        for i, row in enumerate(raw):
            if not isinstance(row, dict):
                raise ValueError("Invalid map frame.")
            frame = MapFrame(i + 1, str(row.get("name", f"Map {i + 1}"))[:60] or f"Map {i + 1}",
                             *(number(row.get(key), 20) for key in ("x", "y", "width", "height")),
                             row.get("view", {}) if isinstance(row.get("view", {}), dict) else {})
            plan.constrain(frame)
            plan.frames.append(frame)
        return plan

    def steps(self):
        pw, ph = self.page_size
        rows = "\n".join(f"{f.name}: X {f.x:.1f}; Y {f.y:.1f}; width {f.width:.1f}; height {f.height:.1f} mm" for f in self.frames)
        return (f"QGIS layout — {self.size} {self.orientation} ({pw:g} × {ph:g} mm)\n\n"
                f"1. Project → New Print Layout. Set Page Properties to {self.size}, {self.orientation}.\n"
                "2. Add Item → Add Map. In Item Properties → Position and Size, choose the top-left reference point and mm units.\n"
                f"{rows}\n"
                "3. Set each map's extent from the main canvas, then adjust its scale or use Move Item Content.\n"
                "4. Enable Lock layers and Lock styles for layers for each map to keep its appearance independent.\n"
                "5. Add any title, legend or scale bar, then Layout → Export as PDF or Export as Image.\n\n"
                "Or click Create Layout in this plugin to create these map items directly from their captured views.\n"
                f"Margin {self.margin:g} mm. Arrangement gap {self.gap:g} mm; manual edits can change actual gaps.")
