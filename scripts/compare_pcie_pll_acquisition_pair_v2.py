#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fixed raw-phase comparison: same2.5ps TSTEP,2.5ps versus1.25ps TMAX."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path

import compare_pcie_pll_acquisition_pair_v1 as previous
import characterize_pcie_pll_acquisition_v4 as producer

PREVIOUS_SHA = '7d20c187e38e515cf8876a286bb53effc1e4322071ace8a60463d9e48c78b506'
REVIEWER_SHA = 'c52432fa751dd7d60bb1907d81ab2982eb28da5eb4513c0c7cfeb6869cebc01a'
require, pin, compare = previous.require, previous.pin, previous.compare
WINDOWS, FREQUENCY_LIMIT_PPM, PHASE_LIMIT_S = previous.WINDOWS, previous.FREQUENCY_LIMIT_PPM, previous.PHASE_LIMIT_S
require(pin(previous.__file__)['sha256'] == PREVIOUS_SHA, 'Frozen pair arithmetic')
namespace = dict(vars(previous))
namespace.update(REVIEWER_SHA=REVIEWER_SHA)
before = inspect.getsource(previous.load_verified)
after = before.replace("Path(p).name == 'review_pcie_pll_acquisition_v1.py'", "Path(p).name == 'review_pcie_pll_acquisition_v2.py'")
require(before != after and after.replace("Path(p).name == 'review_pcie_pll_acquisition_v2.py'", "Path(p).name == 'review_pcie_pll_acquisition_v1.py'") == before, 'One exact reviewer identity bridge')
exec(compile(after, __file__ + ':load_verified', 'exec'), namespace)
load_tight_verified = namespace['load_verified']
BRIDGE = dict(original_sha256=hashlib.sha256(before.encode()).hexdigest(),
              modified_sha256=hashlib.sha256(after.encode()).hexdigest())


def run(first, first_review, second, second_review, declaration):
    require(pin(Path(first)/'result.json')['sha256'] == producer.BASELINE_SHA, 'Exact retained2.5ps native baseline')
    require(pin(first_review)['sha256'] == producer.BASELINE_REVIEW_SHA, 'Exact retained full159part replay')
    d = json.loads(Path(declaration).read_text())
    require(d == dict(
        schema='PLL_RETAINED_TSTEP_MAXSTEP_REFINEMENT_V1',
        first_result_sha256=producer.BASELINE_SHA, first_full_review_sha256=producer.BASELINE_REVIEW_SHA,
        TSTEP_s=2.5e-12, first_TMAX_s=2.5e-12, second_TMAX_s=1.25e-12, stop_s=1e-6,
        windows_s=[[800e-9,900e-9],[900e-9,1e-6]],
        frequency_difference_limit_ppm=100.0, matched_phase_limit_s=50e-12,
        phase_alignment_or_offset_removal=False,
        previous_5ps_2p5ps_pair_status='FAIL_FINITE_NOMINAL_TIMESTEP_SCREEN'), 'Exact rawphase maxstep declaration')
    a, qa = previous.load_verified(first, first_review)
    b, qb = load_tight_verified(second, second_review)
    require(a['config']['step_s'] == b['config']['step_s'] == 2.5e-12, 'Same retainedTSTEP')
    require(b['config'].get('max_step_s') == 1.25e-12 and 'max_step_s' not in a['config'], 'Only declared maxstep refinement')
    require(a['config'] == {k:v for k,v in b['config'].items() if k != 'max_step_s'}, 'Entire physical/numerical config unchanged exceptTMAX')
    require(a['config']['stop_s'] == b['config']['stop_s'] == 1e-6, 'Complete1us comparison')
    require(a['devices'] == b['devices'], 'Same539 physical graph')
    for p in a['inputs'].keys() & b['inputs'].keys():
        require(a['inputs'][p] == b['inputs'][p], 'Unchanged common input: '+p)
    declaration_path = str(Path(declaration).resolve())
    require(b['inputs'].get(declaration_path) == pin(declaration), 'Declaration actually pinned before native run')
    old, new = (Path(first)/'bench.cir').read_text(), (Path(second)/'bench.cir').read_text()
    line = '.tran 2.5e-12 1e-06 0 2.5e-12\n'
    require(old.count(line) == 1 and old.replace(line, '.tran 2.5e-12 1e-06 0 1.25e-12\n') == new, 'Wholedeck exact onlyTMAX inverse')
    for folder in (first, second):
        payload = (Path(folder)/'op.raw').read_bytes().split(b'Binary:\n',1)[1]
        require(len(payload) == 825*8, 'Complete solvedOP payload')
        if folder == first:
            original_op = payload
        else:
            require(payload == original_op, 'Byteidentical solved initialOP')
    result = compare(qa['independent'], qb['independent'])
    result.update(status='PASS_FINITE_RETAINED_TSTEP_MAXSTEP_SCREEN' if result['passed'] else 'FAIL_FINITE_RETAINED_TSTEP_MAXSTEP_SCREEN',
                  original_failed_pair_unchanged=True, no_phase_alignment_or_offset_removal=True,
                  inputs={str(Path(p)):pin(p) for p in [Path(__file__), producer.__file__, previous.__file__, declaration,
                           Path(first)/'result.json', first_review, Path(second)/'result.json', second_review]},
                  scope='Finite nominal1us maximum-step convergence screen; same TSTEP and initialOP. Not PVT/jitter/layout/SOA/completePLL qualification.')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['first','first-review','second','second-review','declaration','out']:
        parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args()
    require(not a.out.exists(), 'Fresh maxstep comparison output')
    result=run(a.first,a.first_review,a.second,a.second_review,a.declaration)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
