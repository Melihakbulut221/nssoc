#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Finite three-conductor field-matrix diagnostics, never RC qualification.

The solver stopping norm and pairwise reciprocity are separate checks. The
unmodified raw matrix is reported. Positive definiteness of its symmetric
part is only a diagnostic and cannot excuse failed raw reciprocity.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'hw/soc/flow'))
from check_fastercap_completion import check as native_completion  # noqa: E402

NAMES = ['g1_subs', 'g2_A', 'g3_B']
RECIPROCITY_LIMIT = .005


def require(condition, message):
    if not condition:
        raise ValueError(message)


def matrix_checks(names, matrix):
    require(names == NAMES, 'Exact subs/A/B conductor order required')
    require(len(matrix) == 3 and all(len(row) == 3 for row in matrix),
            'Exact three-by-three matrix required')
    require(all(type(v) in (int, float) and math.isfinite(v)
                for row in matrix for v in row), 'Finite numeric matrix required')
    scale = max(abs(v) for row in matrix for v in row)
    require(scale > 0, 'Zero matrix')
    require(all(matrix[i][i] > 0 for i in range(3)), 'Positive diagonal required')
    require(all(matrix[i][j] < 0 for i in range(3) for j in range(3) if i != j),
            'Strict negative mutual terms required for this finite geometry')
    row_sums = [math.fsum(row) for row in matrix]
    require(all(v > 0 for v in row_sums), 'Strict positive row sums required')
    pairs = []
    for i, j in [(0, 1), (0, 2), (1, 2)]:
        a, b = matrix[i][j], matrix[j][i]
        relative = abs(a - b) / max(abs(a), abs(b))
        pairs.append(dict(conductors=[names[i], names[j]], forward_F=a,
                          reverse_F=b, relative_difference=relative,
                          within_limit=relative <= RECIPROCITY_LIMIT))
    # Scaling avoids underflow when taking determinants of femtofarad values.
    symmetric = [[(matrix[i][j] + matrix[j][i]) / (2 * scale)
                  for j in range(3)] for i in range(3)]
    a, b, c = symmetric[0]
    _, d, e = symmetric[1]
    _, _, f = symmetric[2]
    minors = [a, a * d - b * b,
              a * (d * f - e * e) - b * (b * f - e * c) + c * (b * e - d * c)]
    positive = all(v > 0 and math.isfinite(v) for v in minors)
    reciprocal = all(p['within_limit'] for p in pairs)
    return dict(raw_matrix_F=matrix, raw_row_sums_F=row_sums,
                raw_exactly_symmetric=all(p['relative_difference'] == 0 for p in pairs),
                pairwise_reciprocity_limit=RECIPROCITY_LIMIT,
                pairwise_reciprocity=pairs, raw_reciprocity_within_limit=reciprocal,
                symmetric_part_scaled_leading_principal_minors=minors,
                symmetric_part_scale_F=scale,
                symmetric_part_positive_definite=positive,
                raw_matrix_was_modified=False,
                finite_matrix_checks_pass=reciprocal and positive,
                symmetric_part_is_not_a_replacement_for_raw_matrix=True)


def audit(text, returncode, solver_tolerance):
    require(solver_tolerance in (.005, .0025, .001), 'Only frozen or tighter solver tolerance')
    native = native_completion(text, returncode, solver_tolerance)
    values = matrix_checks(native['conductors'], native['matrix_F'])
    return dict(status=('PASS_FINITE_MATRIX_DIAGNOSTICS_ONLY'
                        if values['finite_matrix_checks_pass']
                        else 'FAIL_RAW_MATRIX_RECIPROCITY_OR_SYMMETRIC_PART'),
                native=native, matrix=values, qualified_rc=False,
                calibrated_process_model=False, domain_convergence_proved=False,
                tolerance_is_not_physical_accuracy=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--log', type=Path, required=True)
    p.add_argument('--returncode', type=int, required=True)
    p.add_argument('--solver-tolerance', type=float, choices=[.005, .0025, .001], required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    require(not args.out.exists(), 'Refusing to overwrite an audit')
    try:
        result = audit(args.log.read_text(), args.returncode, args.solver_tolerance)
    except (ValueError, OSError) as error:
        result = dict(status='REJECTED_FIELD_RESULT', error=str(error), qualified_rc=False)
    result['input_sha256'] = {
        str(x.resolve()): hashlib.sha256(x.read_bytes()).hexdigest()
        for x in [Path(__file__), ROOT / 'hw/soc/flow/check_fastercap_completion.py', args.log]}
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'])
    return 0 if result['status'].startswith('PASS_') else 2


if __name__ == '__main__':
    raise SystemExit(main())
