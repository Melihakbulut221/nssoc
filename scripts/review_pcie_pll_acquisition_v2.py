#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Full lossless replay of the distinct1.25ps maximum-step experiment.

The independent edge/window arithmetic and exact full539device author replay
remain unchanged. Only the explicit TMAX producer and its metadata are bound.
"""
import hashlib
import inspect
from pathlib import Path

import review_pcie_pll_acquisition_v1 as previous
import characterize_pcie_pll_acquisition_v4 as producer

PREVIOUS_SHA = '168a1563ed1847e752c67e3058b823200bfe2b3f4e2b345046a0ed13318530db'
PRODUCER_SHA = '5e64b71eeb9f792b1a909ec354b3c69010b6f0983ec4f36323b2e0992c2b5503'
require = previous.require
BRIDGES = {}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


require(sha(previous.__file__) == PREVIOUS_SHA, 'Frozen complete replayV1')
require(sha(producer.__file__) == PRODUCER_SHA, 'Frozen maxstep producerV4')
namespace = dict(vars(previous))
namespace.update(__file__=__file__, __name__=__name__, __doc__=__doc__,
                 producer=producer, PRODUCER_SHA=PRODUCER_SHA)


def derive(name, replacements):
    source = original = inspect.getsource(getattr(previous, name))
    for before, after in replacements:
        require(source.count(before) == 1, 'Unique maxstep replay bridge: ' + name)
        source = source.replace(before, after)
    BRIDGES[name] = dict(original_sha256=hashlib.sha256(original.encode()).hexdigest(),
                        modified_sha256=hashlib.sha256(source.encode()).hexdigest(),
                        exact_replacements=replacements)
    exec(compile(source, __file__ + ':' + name, 'exec'), namespace)
    return namespace[name]


bind_completed_capture = derive('bind_completed_capture', [
    ('record["config"]["step_s"] in (5e-12, 2.5e-12)',
     'record["config"]["step_s"] == 2.5e-12 and record["config"]["max_step_s"] == 1.25e-12'),
    ('step_s=record["config"]["step_s"],',
     'step_s=record["config"]["step_s"], max_step_s=1.25e-12,'),
    ('original = producer.previous.previous.ORIGINAL', 'original = producer.namespace["ORIGINAL"]'),
])
review = derive('review', [
    ('record["config"]["step_s"] in [5e-12, 2.5e-12]',
     'record["config"]["step_s"] == 2.5e-12 and record["config"]["max_step_s"] == 1.25e-12'),
    ('producer.previous.Meter(columns, record["devices"], record["config"])',
     'producer.Meter(columns, record["devices"], record["config"])'),
    ('producer.previous.canonical_indices(columns)', 'producer.namespace["canonical_indices"](columns)'),
])
main = derive('main', [])
independent_edges = previous.independent_edges
monotone_ordinals = previous.monotone_ordinals
independent_analysis = previous.independent_analysis
compare_independent = previous.compare_independent
decode_part = previous.decode_part

if __name__ == '__main__':
    raise SystemExit(main())
