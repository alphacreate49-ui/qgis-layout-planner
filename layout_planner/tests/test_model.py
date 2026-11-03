# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Muhammad Naeem

import itertools
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from layout_planner.model import PAGE_SIZES, MapFrame, Plan
from layout_planner.selftest import _require


class GeometryTests(unittest.TestCase):
    def test_smoke_validation_raises_for_failed_conditions(self):
        _require(True, "This check must pass")
        with self.assertRaisesRegex(AssertionError, "Smoke check failed"):
            _require(False, "Smoke check failed")

    def test_all_page_arrangements_stay_in_bounds_and_have_no_overlap(self):
        combinations = itertools.product(PAGE_SIZES, ("portrait", "landscape"), (2, 3),
                                         ("feature", "columns", "rows"), (0, 12, 34, 999), (0, 6, 30, 999))
        cases = 0
        for size, orientation, count, preset, margin, gap in combinations:
            plan = Plan(size=size, orientation=orientation, count=count, preset=preset, margin=margin, gap=gap)
            plan.arrange()
            self.assertEqual(len(plan.frames), count)
            self.assertEqual(plan.overlaps(), [])
            pw, ph = plan.page_size
            for frame in plan.frames:
                self.assertGreaterEqual(frame.width + 1e-8, 20)
                self.assertGreaterEqual(frame.height + 1e-8, 20)
                self.assertGreaterEqual(frame.x + 1e-8, plan.margin)
                self.assertGreaterEqual(frame.y + 1e-8, plan.margin)
                self.assertLessEqual(frame.right, pw - plan.margin + 1e-8)
                self.assertLessEqual(frame.bottom, ph - plan.margin + 1e-8)
            cases += 1
        self.assertEqual(cases, 960)

    def test_physical_page_coordinates(self):
        plan = Plan()
        plan.arrange()
        self.assertEqual(plan.page_size, (297, 210))
        a, b, c = plan.frames
        self.assertEqual((a.x, a.y, a.height), (12, 12, 186))
        self.assertAlmostEqual(b.x - a.right, 6)
        self.assertAlmostEqual(c.y - b.bottom, 6)

    def test_move_is_constrained(self):
        plan = Plan()
        frame = MapFrame(1, "test", -500, 999, 80, 60)
        plan.constrain(frame)
        self.assertEqual((frame.x, frame.y), (12, 138))

    def test_all_resize_handles_respect_minimum_and_page_bounds(self):
        plan = Plan()
        original = MapFrame(1, "test", 50, 50, 80, 60)
        for handle in ("nw", "ne", "sw", "se"):
            for delta in (-999, 999):
                frame = MapFrame(1, "test", 50, 50, 80, 60)
                plan.resize(frame, original, handle, delta, delta)
                self.assertGreaterEqual(frame.width, 20)
                self.assertGreaterEqual(frame.height, 20)
                self.assertGreaterEqual(frame.x, 12)
                self.assertGreaterEqual(frame.y, 12)
                self.assertLessEqual(frame.right, 285)
                self.assertLessEqual(frame.bottom, 198)

    def test_overlap_detection_allows_a_shared_edge(self):
        plan = Plan(frames=[MapFrame(1, "a", 12, 12, 50, 50), MapFrame(2, "b", 62, 12, 50, 50)])
        self.assertEqual(plan.overlaps(), [])
        plan.frames[1].x = 61
        self.assertEqual(plan.overlaps(), [(1, 2)])

    def test_reflow_preserves_map_names_and_independent_views(self):
        plan = Plan()
        plan.arrange()
        plan.frames[0].name = "Punjab"
        plan.frames[0].view = {"layers": ["roads"], "extent": [1, 2, 3, 4]}
        old = plan.frames[0]
        plan.preset = "columns"
        plan.arrange()
        self.assertEqual(plan.frames[0].name, "Punjab")
        self.assertEqual(plan.frames[0].view, old.view)
        plan.frames[0].view["layers"].append("rivers")
        self.assertEqual(old.view["layers"], ["roads"])

    def test_plan_roundtrip_preserves_geometry_and_views(self):
        plan = Plan(size="Letter", count=2, name="District sheet")
        plan.arrange()
        plan.frames[0].width = 90.2
        plan.frames[0].view = {"extent": [0, 0, 10, 10], "layers": ["a"], "styles": {"a": "<xml/>"}}
        loaded = Plan.from_json(plan.to_json())
        self.assertEqual(loaded, plan)

    def test_invalid_numbers_and_unknown_settings_are_normalized(self):
        plan = Plan.from_json('{"size":"bad","orientation":"bad","margin":999,"gap":999,"count":9,"frames":[]}')
        self.assertEqual(plan.size, "A4")
        self.assertEqual(plan.count, 3)
        self.assertEqual(plan.overlaps(), [])
        self.assertEqual(len(plan.frames), 3)
        with self.assertRaises(ValueError):
            Plan.from_json('[]')

    def test_guide_uses_edited_geometry_and_top_left_reference(self):
        plan = Plan()
        plan.arrange()
        plan.frames[0].x = 14.3
        text = plan.steps()
        self.assertIn("X 14.3", text)
        self.assertIn("top-left reference point", text)
        self.assertIn("Create Layout", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
