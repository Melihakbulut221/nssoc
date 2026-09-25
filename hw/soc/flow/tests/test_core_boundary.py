# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""The density outline must represent the actual die without changing masks."""
from pathlib import Path
import sys

import unittest
import tempfile
import klayout.db as db

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from normalize_core_boundary import normalize


def layout_file(path, outside=False, multiple=False, outline=True):
    layout = db.Layout()
    layout.dbu = .001
    top = layout.create_cell('soc_top')
    macro = layout.create_cell('macro')
    macro.shapes(layout.layer(189, 0)).insert(db.Box(0, 0, 2000, 2000))
    macro.shapes(layout.layer(8, 0)).insert(db.Box(100, 100, 1500, 1500))
    macro.shapes(layout.layer(8, 25)).insert(db.Text('vdd', db.Trans(500, 500)))
    top.insert(db.CellInstArray(macro.cell_index(), db.Trans(1000, 1000)))
    top.insert(db.CellInstArray(macro.cell_index(), db.Trans(5000, 5000)))
    if outline:
        top.shapes(layout.layer(189, 4)).insert(db.Box(0, 0, 10000, 10000))
    if multiple:
        top.shapes(layout.layer(189, 4)).insert(db.Box(100, 100, 200, 200))
    if outside:
        top.shapes(layout.layer(8, 0)).insert(db.Box(-100, 0, 100, 200))
    layout.write(str(path))


class BoundaryTests(unittest.TestCase):
    def test_exact_die_preserves_masks_text_and_instances(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root/'source.gds', root/'target.gds'
            layout_file(source)
            result = normalize(source, target, 'soc_top')
            self.assertTrue(result['unchanged_other_layers_text_and_hierarchy'])
            self.assertEqual(result['original_die_box_dbu'], [0, 0, 10000, 10000])
            self.assertEqual(result['inherited_boundary_shapes_removed'], {'macro': 1})
            self.assertFalse(result['manufacturing_acceptance'])
            layout = db.Layout()
            layout.read(str(target))
            index = layout.find_layer(189, 0)
            self.assertTrue(layout.cell('macro').shapes(index).is_empty())
            self.assertEqual(layout.cell('soc_top').shapes(index).size(), 1)

    def rejected(self, **kwargs):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'source.gds'
            layout_file(source, **kwargs)
            with self.assertRaises(ValueError):
                normalize(source, Path(directory)/'invalid.gds', 'soc_top')

    def test_outside_material_is_not_cropped(self):
        self.rejected(outside=True)

    def test_ambiguous_die_rejected(self):
        self.rejected(multiple=True)

    def test_missing_die_rejected(self):
        self.rejected(outline=False)


if __name__ == '__main__':
    unittest.main()
