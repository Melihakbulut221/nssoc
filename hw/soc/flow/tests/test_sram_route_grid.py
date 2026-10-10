# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native GDS controls for bounded, source-bound SRAM route edits."""
from pathlib import Path
import copy
import sys
import tempfile
import unittest

import klayout.db as db

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from repair_sram_route_grid import digest, repair, rounded_polygon, EXPECTED


class RouteGridTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base/'source.gds'
        layout = db.Layout()
        layout.dbu = .001
        top = layout.create_cell('soc_top')
        top.shapes(layout.layer(189, 0)).insert(db.Box(-100, -100, 1000, 1000))
        for name, count in EXPECTED.items():
            cell = layout.create_cell(name)
            for index in range(count):
                cell.shapes(layout.layer(10, 0)).insert(db.Box(index*100, 0, index*100+22, 20))
            cell.shapes(layout.layer(10, 2)).insert(db.Text('pin', db.Trans(10, 10)))
            cell.shapes(layout.layer(1, 0)).insert(db.Box(0, 100, 40, 140))
            top.insert(db.CellInstArray(cell.cell_index(), db.Trans()))
        layout.write(str(self.source))
        loaded = db.Layout()
        loaded.read(str(self.source))
        targets = [dict(cell=name, layer='10/0', polygon=s.polygon.to_s())
                   for name in EXPECTED
                   for s in loaded.cell(name).shapes(loaded.layer(10, 0)).each()]
        self.audit = dict(input_sha256={str(self.source): digest(self.source)},
                          dbu_um=.001, grid_dbu=5, offgrid_instances=[], offgrid_polygons=targets)

    def test_serialized_repair_and_original_source_preservation(self):
        result = repair(self.source, self.audit, self.base/'repaired')
        self.assertEqual(len(result['modifications']), 6)
        self.assertTrue(all(r['maximum_displacement_nm'] == 2 for r in result['modifications']))
        self.assertFalse(result['full_drc_lvs_timing_acceptance'])
        self.assertEqual(digest(self.source), self.audit['input_sha256'][str(self.source)])
        loaded = db.Layout()
        loaded.read(str(self.base/'repaired/soc_top.gds'))
        for name in EXPECTED:
            for shape in loaded.cell(name).shapes(loaded.layer(10, 0)).each():
                self.assertTrue(all(p.x % 5 == p.y % 5 == 0 for p in shape.polygon.each_point_hull()))
            self.assertEqual(loaded.cell(name).shapes(loaded.layer(10, 2)).size(), 1)
            self.assertEqual(loaded.cell(name).shapes(loaded.layer(1, 0)).size(), 1)

    def test_reject_changed_source_receipt(self):
        bad = copy.deepcopy(self.audit)
        bad['input_sha256'][str(self.source)] = '0'*64
        with self.assertRaisesRegex(ValueError, 'bound to this source'):
            repair(self.source, bad, self.base/'bad')

    def test_reject_unapproved_geometry_scope(self):
        for fault in ['layer', 'cell', 'instance', 'duplicate']:
            with self.subTest(fault=fault):
                bad = copy.deepcopy(self.audit)
                if fault == 'layer':
                    bad['offgrid_polygons'][0]['layer'] = '1/0'
                elif fault == 'cell':
                    bad['offgrid_polygons'][0]['cell'] = 'logic_cell'
                elif fault == 'instance':
                    bad['offgrid_instances'] = [{'child': 'logic_cell'}]
                else:
                    bad['offgrid_polygons'][1] = bad['offgrid_polygons'][0]
                with self.assertRaises(ValueError):
                    repair(self.source, bad, self.base/fault)

    def test_reject_collapsed_or_clean_polygon(self):
        for box in [db.Box(0, 0, 1, 20), db.Box(0, 0, 20, 20)]:
            with self.assertRaises(ValueError):
                rounded_polygon(db.Polygon(box))


if __name__ == '__main__':
    unittest.main()
