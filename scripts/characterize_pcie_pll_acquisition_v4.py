#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Distinct maximum-step experiment: retained2.5ps TSTEP,1.25ps TMAX,1us.

The original5ps/2.5ps phase comparison remains failed. This version changes
only TMAX and the corresponding strict metadata/grid checks, with all native
devices, startup, numerical tolerances, safety and acquisition limits frozen.
"""
import hashlib
import inspect
import json
from pathlib import Path

import characterize_pcie_pll_acquisition_v3 as previous
import compare_pcie_pll_acquisition_pair_v1 as pair

PREVIOUS_SHA = 'd3b6706d0b8feb1c6a5c66bb434df29fe792b621200eae8fc593ea5e4faa9b8d'
PAIR_SHA = '7d20c187e38e515cf8876a286bb53effc1e4322071ace8a60463d9e48c78b506'
BASELINE_SHA = '072c0b6d8f0c4ae231e7f7160d63a6356c797dda0b438ec6aa68d4a279303b43'
BASELINE_REVIEW_SHA = 'b4bf9c2457a988ff9c0693f639fc98ed56c744a4e7d379cd38b9465b50affb52'
TSTEP = 2.5e-12
TMAX = 1.25e-12
STOP = 1e-6
base = previous.previous.previous
require, life, n = previous.require, previous.life, base.n
publication, runtime = previous.publication, previous.runtime
RELEASE_TAG = previous.RELEASE_TAG
BRIDGES = {}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_parent():
    require(sha(previous.__file__) == PREVIOUS_SHA, 'Frozen acquisitionV3')
    require(sha(pair.__file__) == PAIR_SHA, 'Frozen baseline receipt verifier')
    return previous.verify_parent()


def stream_deck(original, step, stop):
    require(step == TSTEP and stop == STOP, 'Fixed2.5ps TSTEP and1us analysis')
    text = previous.stream_deck(original, step, stop)
    old = '.tran 2.5e-12 1e-06 0 2.5e-12\n'
    require(text.count(old) == 1, 'One exact retainedTSTEP/maxstep bridge')
    return text.replace(old, '.tran 2.5e-12 1e-06 0 1.25e-12\n')


def prerequisites(manifest, digest, step, prior):
    require(step == TSTEP, 'Fixed retainedTSTEP')
    require(sha(manifest) == digest, 'Externally pinned maxstep prerequisite manifest')
    d = json.loads(Path(manifest).read_text())
    require(set(d) == {'parent', 'baseline', 'baseline_review', 'declaration'}, 'Exact maxstep prerequisites')
    for v in d.values():
        require(set(v) == {'path', 'sha256'}, 'Exact path and digest')
        require(sha(v['path']) == v['sha256'], 'Pinned maxstep prerequisite bytes')
    require(d['baseline']['sha256'] == BASELINE_SHA, 'Exact retained2.5ps native baseline')
    require(d['baseline_review']['sha256'] == BASELINE_REVIEW_SHA, 'Exact full159part replay baseline')
    a, q = pair.load_verified(Path(d['baseline']['path']).parent, d['baseline_review']['path'])
    require(a['config']['step_s'] == TSTEP and a['config']['stop_s'] == STOP and 'max_step_s' not in a['config'], 'Unchanged original baseline analysis')
    require(a['devices'] == prior['devices'], 'Exact baseline539device graph')
    declaration = json.loads(Path(d['declaration']['path']).read_text())
    require(declaration == dict(
        schema='PLL_RETAINED_TSTEP_MAXSTEP_REFINEMENT_V1',
        first_result_sha256=BASELINE_SHA, first_full_review_sha256=BASELINE_REVIEW_SHA,
        TSTEP_s=TSTEP, first_TMAX_s=TSTEP, second_TMAX_s=TMAX, stop_s=STOP,
        windows_s=[[800e-9, 900e-9], [900e-9, 1e-6]],
        frequency_difference_limit_ppm=100.0, matched_phase_limit_s=50e-12,
        phase_alignment_or_offset_removal=False,
        previous_5ps_2p5ps_pair_status='FAIL_FINITE_NOMINAL_TIMESTEP_SCREEN'), 'Exact predeclared rawphase/frequency screen')
    parent = previous.prerequisites(d['parent']['path'], d['parent']['sha256'], step, prior)
    paths = parent['paths'] + [str(manifest), str(Path(pair.__file__).resolve())]
    paths += [v['path'] for v in d.values()] + list(q['inputs'])
    paths += [str(Path(d['baseline']['path']).parent / p) for p in a['outputs']]
    return dict(paths=sorted(set(paths)), manifest=d)


require(sha(previous.__file__) == PREVIOUS_SHA, 'Exact acquisitionV3 source')
require(sha(pair.__file__) == PAIR_SHA, 'Exact baseline verifier source')
namespace = dict(previous.namespace)
namespace.update(__file__=__file__, __name__=__name__, __doc__=__doc__,
                 verify_parent=verify_parent, stream_deck=stream_deck,
                 prerequisites=prerequisites, TSTEP=TSTEP, TMAX=TMAX)


def bridge(source, replacements, name):
    original = source
    for before, after in replacements:
        require(source.count(before) == 1, 'Unique maxstep source bridge: ' + name)
        source = source.replace(before, after)
    BRIDGES[name] = dict(original_sha256=hashlib.sha256(original.encode()).hexdigest(),
                        modified_sha256=hashlib.sha256(source.encode()).hexdigest(),
                        exact_replacements=replacements)
    return source


# Same complete native safety reducer; only the grid ceiling uses explicitTMAX.
meter_source = bridge(inspect.getsource(previous.namespace['Meter']),
                      [('self.config["step_s"] * (1 + 1e-5)',
                        'self.config["max_step_s"] * (1 + 1e-5)')], 'Meter')
exec(compile(meter_source, __file__ + ':Meter', 'exec'), namespace)
Meter = namespace['Meter']
# Rebind the unchanged complete capture body to this private namespace.
capture_source = inspect.getsource(base.previous.previous.capture)
for before, after in base.BRIDGES['capture']['exact_replacements']:
    require(capture_source.count(before) == 1, 'Exact inherited capture construction')
    capture_source = capture_source.replace(before, after)
require(hashlib.sha256(capture_source.encode()).hexdigest() == base.BRIDGES['capture']['modified_sha256'], 'Exact inherited capture body')
exec(compile(capture_source, __file__ + ':capture', 'exec'), namespace)
capture = namespace['capture']

# Memory advisory sizing is based on TSTEP, not TMAX; its exact parser stays.
startup_source = bridge(inspect.getsource(base.startup_proof), [
    ('len(analyses) == 1 and analyses[0][0] == analyses[0][2]',
     "analyses == [('2.5e-12', '1e-06', '1.25e-12')]"),
], 'startup_proof')
startup_namespace = dict(vars(base))
exec(compile(startup_source, __file__ + ':startup_proof', 'exec'), startup_namespace)
startup_proof = startup_namespace['startup_proof']
namespace['startup_proof'] = startup_proof

run_source = bridge(previous.run_source, [
    ("stop == 1e-6 and step in (5e-12, 2.5e-12)", 'stop == STOP and step == TSTEP'),
    ("step_s=step, stop_s=stop, window_s=[4e-9, stop])",
     "step_s=step, max_step_s=TMAX, stop_s=stop, window_s=[4e-9, stop])"),
    ('+ [__file__, str(publication.__file__), str(publication.lifecycle.__file__), str(reference)]',
     '+ [__file__, str(Path(previous.__file__).resolve()), str(publication.__file__), str(publication.lifecycle.__file__), str(reference)]'),
], 'run')
namespace['previous'] = previous
exec(compile(run_source, __file__ + ':run', 'exec'), namespace)
run = namespace['run']
main_source = bridge(previous.main_source, [
    ('choices=[5, 2.5]', 'choices=[2.5]'),
    ('{5: 5e-12, 2.5: 2.5e-12}[args.step_ps]', '{2.5: 2.5e-12}[args.step_ps]'),
], 'main')
exec(compile(main_source, __file__ + ':main', 'exec'), namespace)
main = namespace['main']
measurements, acquisition = previous.measurements, previous.acquisition
OwnedPublisherV3 = previous.OwnedPublisherV3

if __name__ == '__main__':
    raise SystemExit(main())
