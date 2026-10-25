#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run marker repair/preservation controls with KLayout's Python runtime."""
import argparse
import json
from pathlib import Path
import sys

import klayout.db as db

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hw/soc/flow'))
from repair_io_resistor_markers import EXPECTED, repair, verify_preservation


def fixture():
    layout = db.Layout()
    layout.dbu = .001
    for name, boxes in EXPECTED.items():
        cell = layout.create_cell(name)
        for layer in [(5, 0), (28, 0), (14, 0), (111, 0)]:
            for box in boxes:
                cell.shapes(layout.layer(*layer)).insert(db.Box(*box))
        cell.shapes(layout.layer(10, 25)).insert(db.Text('pad', db.Trans()))
    return layout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    original = fixture()
    positive = original.dup()
    assert sum(repair(positive).values()) == 27
    verify_preservation(original, positive)
    rejected = []
    for fault in ['existing_marker', 'missing_extblock', 'wrong_length', 'active_overlap',
                  'mask_change', 'text_change', 'missing_added_marker', 'moved_instance']:
        layout = fixture()
        cell = layout.cell('sg13g2_SecondaryProtection')
        if fault == 'existing_marker':
            cell.shapes(layout.layer(128, 0)).insert(db.Box(940, 1370, 1940, 3370))
        elif fault == 'missing_extblock':
            cell.shapes(layout.layer(111, 0)).clear()
        elif fault == 'wrong_length':
            cell.shapes(layout.layer(5, 0)).clear()
            cell.shapes(layout.layer(5, 0)).insert(db.Box(940, 1370, 1940, 3000))
        elif fault == 'active_overlap':
            cell.shapes(layout.layer(1, 0)).insert(db.Box(940, 1370, 1940, 3370))
        else:
            repair(layout)
            if fault == 'mask_change':
                cell.shapes(layout.layer(10, 0)).insert(db.Box(0, 0, 100, 100))
            elif fault == 'text_change':
                cell.shapes(layout.layer(10, 25)).clear()
            elif fault == 'missing_added_marker':
                cell.shapes(layout.layer(128, 0)).clear()
            elif fault == 'moved_instance':
                cell.insert(db.CellInstArray(layout.cell('sg13g2_RCClampResistor').cell_index(),
                                             db.Trans(100, 200)))
        try:
            if fault in ['existing_marker', 'missing_extblock', 'wrong_length', 'active_overlap']:
                repair(layout)
            else:
                verify_preservation(original, layout)
        except ValueError as error:
            rejected.append({'fault': fault, 'error': str(error)})
        else:
            raise AssertionError('Fault accepted: ' + fault)
    result = {'status': 'PASS_ONE_VALID_REPAIR_EIGHT_FAULTS_REJECTED', 'rejected': rejected}
    (args.output / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(result['status'])


if __name__ == '__main__':
    main()
