# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Plot completed finite captures only; no fitted phase or extrapolation."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

R = Path.cwd()
B = Path(__file__).resolve().parent
E = R / 'hw/soc/out/pcie-vco-v6-divider-tail115-v1-eighthstep-20261006'

def pin(p):
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size,
                    sha256=hashlib.file_digest(f, 'sha256').hexdigest())

comparison = json.loads((E / 'step-comparison01.json').read_text())
numerical = json.loads((E / 'numerical-convergence01.json').read_text())
policy = json.loads((E / 'numerical-policy01.json').read_text())
captures = comparison['captures']
assert [x['step_s'] for x in captures] == [5e-12, 2.5e-12, 1.25e-12, 6.25e-13]
assert numerical['status'] == 'FAIL_FINITE_OPEN_LOOP_NUMERICAL_SCREEN'
assert policy['frequency_limit_ppm'] == 100 and policy['phase_limit_ps'] == 50
for c in captures:
    assert c['electrical_pass'] and c['initial_mapping']['vco_before_window'] == 30
    assert c['initial_mapping']['first_cml_nearest_global_vco'] == 31
    assert len(c['numerical_edge_times']['cml']) == 61
    for p, expected in c['source_inputs'].items():
        assert pin(Path(p)) == expected

plt.rcParams.update({'font.size': 11, 'axes.spines.top': False,
                     'axes.spines.right': False})
fig, (a, b) = plt.subplots(1, 2, figsize=(13, 6.4), constrained_layout=False)
fig.subplots_adjust(left=.075, right=.98, bottom=.27, top=.78, wspace=.28)
steps = np.array([x['step_s'] * 1e12 for x in captures])
frequency = np.array([x['vco_frequency_hz'] / 1e9 for x in captures])
a.plot(steps, frequency, color='#526579', lw=1.8, zorder=1)
for idx, c in enumerate(captures):
    passed = c['native_status'] == 'PASS_NATIVE_LOADED_FEEDBACK_SCREEN'
    a.scatter(steps[idx], frequency[idx], s=65, marker='o' if passed else 'x',
              color='#16765c' if passed else '#b43e31', zorder=3,
              label=('Original functional PASS' if passed else 'Original functional FAIL')
              if idx in (0, 2) else None)
a.set_xscale('log', base=2)
a.set_xlim(5.6, .56)
a.set_xticks(steps, ['5', '2.5', '1.25', '0.625'])
a.set_xlabel('Output and maximum solver step (ps)')
a.set_ylabel('Measured VCO frequency (GHz)')
a.set_title('Measured frequency still changes', loc='left', weight='bold', fontsize=12)
a.grid(alpha=.20)
a.legend(loc='lower right', fontsize=9, frameon=False)

metrics = []
for i, color in enumerate(['#936629', '#7161a8', '#087e8b']):
    old, new = captures[i:i+2]
    phase = (np.asarray(new['numerical_edge_times']['cml']) -
             np.asarray(old['numerical_edge_times']['cml'])) * 1e12
    ppm = abs(new['vco_frequency_hz'] / old['vco_frequency_hz'] - 1) * 1e6
    metrics.append(dict(reference_step_ps=steps[i], candidate_step_ps=steps[i+1],
                        vco_delta_ppm=ppm, max_unaligned_cml_delta_ps=float(abs(phase).max())))
    b.plot(np.arange(61), abs(phase), color=color, lw=2,
           label=f'{steps[i]:g} → {steps[i+1]:g} ps')
b.axhline(50, color='#526579', ls='--', lw=1.2, label='50 ps phase limit')
b.set_xlabel('Matched CML edge index (fixed absolute VCO anchor)')
b.set_ylabel('Absolute raw edge-time difference (ps)')
b.set_title('No fitted phase offset or time shift', loc='left', weight='bold', fontsize=12)
b.set_xlim(0, 60)
b.set_ylim(0, 150)
b.grid(alpha=.20)
b.legend(loc='upper left', fontsize=9, frameon=False)

assert abs(metrics[-1]['vco_delta_ppm'] - numerical['details']['vco_frequency_delta_ppm']) < 1e-8
fig.suptitle('Loaded divider: four complete 34 ns nominal captures',
             x=.075, y=.95, ha='left', weight='bold', fontsize=17)
fig.text(.075, .858,
         f"1.25 → 0.625 ps: VCO changes {metrics[-1]['vco_delta_ppm']:.3f} ppm "
         '(limit 100 ppm); supplementary numerical screen FAIL.', fontsize=11)
fig.text(.075, .065,
         'All 455 electrical screens pass at each step. The two earlier functional FAIL results remain FAIL.\n'
         '50 ps is the separately declared adjacent-step phase limit; frequency and original functional gates also apply.\n'
         'Finite nominal open-loop study only: no PVT, closed-loop acquisition or full PHY acceptance.',
         fontsize=9, linespacing=1.5, color='#354354')
for suffix in ['png', 'svg']:
    fig.savefig(B / ('four-step-comparison02.' + suffix), dpi=160)
plt.close(fig)
result = dict(status='PLOT_FROM_FOUR_COMPLETE_CAPTURES_ORIGINAL_VERDICTS_RETAINED',
              inputs={str(p): pin(p) for p in [Path(__file__), E / 'step-comparison01.json',
                      E / 'numerical-convergence01.json', E / 'numerical-policy01.json']},
              metrics=metrics,
              figures={p.name: pin(p) for p in B.glob('four-step-comparison02.*')},
              numerical_convergence=False, physical_acceptance=False)
(B / 'result02.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(metrics, indent=2))
