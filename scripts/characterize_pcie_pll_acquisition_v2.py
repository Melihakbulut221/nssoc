#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Publication-only continuation of the frozen physical 1us acquisition screen.

V1's 379ns capture stopped on the release's1000-asset limit and remains ERROR.
This version changes only the owned publisher command and its source pin/tag.
Every native device, deck, numerical setting, safety/settling formula, runtime,
resource limit, process owner and lossless FIFO/part algorithm is inherited.
"""

import hashlib
import inspect
from pathlib import Path

import characterize_pcie_pll_acquisition_v1 as previous
import publish_pcie_native_capture_v2 as publication

PREVIOUS_SHA = "ea34d89dc062a515727814b5549d28c4036ca030d39d966aacf605a8691ac649"
PUBLISHER_SHA = "70ea108b29f1fcd07ec6d4759a3caac97db3da862a6d49d4e696154572509bf3"
RELEASE_TAG = "evidence-20261005-pcie-continuation"
require = previous.require
life = previous.namespace["life"]
BRIDGES = {}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_parent():
    require(sha(previous.__file__) == PREVIOUS_SHA, "Frozen acquisition V1")
    require(sha(publication.__file__) == PUBLISHER_SHA, "Frozen continuation publisher")
    require(publication.TAG == RELEASE_TAG, "Declared continuation release")
    return previous.verify_parent()


require(sha(previous.__file__) == PREVIOUS_SHA, "Exact inherited acquisition source")
require(
    sha(publication.__file__) == PUBLISHER_SHA, "Exact continuation publisher source"
)
namespace = dict(previous.namespace)
namespace.update(
    __file__=__file__,
    __name__=__name__,
    __doc__=__doc__,
    verify_parent=verify_parent,
    STOP=previous.STOP,
    runtime=previous.runtime,
)
publisher_namespace = dict(vars(life))
publisher_namespace.update(
    __file__=__file__,
    __name__=__name__,
    publication=publication,
    PUBLISHER_SHA=PUBLISHER_SHA,
    RELEASE_TAG=RELEASE_TAG,
)


def bridge(source, replacements, name):
    original = source
    for old, new in replacements:
        require(
            source.count(old) == 1, "Unique publication-only source bridge: " + name
        )
        source = source.replace(old, new)
    BRIDGES[name] = {
        "original_sha256": hashlib.sha256(original.encode()).hexdigest(),
        "modified_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "exact_replacements": replacements,
    }
    return source


publisher_source = bridge(
    inspect.getsource(life.OwnedPublisher),
    [
        ("class OwnedPublisher:", "class OwnedPublisherV2:"),
        ("== previous.PUBLISHER_SHA", "== PUBLISHER_SHA"),
        (
            'str(Path(publication.__file__)),\n                    "--out",',
            'str(Path(publication.__file__)),\n                    "--tag",\n                    RELEASE_TAG,\n                    "--out",',
        ),
    ],
    "publisher",
)
exec(compile(publisher_source, __file__ + ":publisher", "exec"), publisher_namespace)
OwnedPublisherV2 = publisher_namespace["OwnedPublisherV2"]
namespace["OwnedPublisherV2"] = OwnedPublisherV2
# Reconstruct the exact existing generated V1 run before the one routing change.
run_source = inspect.getsource(previous.previous.previous.run)
for old, new in previous.BRIDGES["run"]["exact_replacements"]:
    require(run_source.count(old) == 1, "Exact inherited run generation")
    run_source = run_source.replace(old, new)
require(
    hashlib.sha256(run_source.encode()).hexdigest()
    == previous.BRIDGES["run"]["modified_sha256"],
    "Exact generated V1 run identity",
)
run_source = bridge(
    run_source,
    [("life.OwnedPublisher(owner)", "OwnedPublisherV2(owner)")],
    "run",
)
exec(compile(run_source, __file__ + ":run", "exec"), namespace)
run = namespace["run"]
main_source = inspect.getsource(previous.main)
exec(compile(main_source, __file__ + ":main", "exec"), namespace)
main = namespace["main"]
# Direct immutable aliases make the unchanged physics/measurement scope explicit.
stream_deck = previous.stream_deck
measurements = previous.measurements
startup_proof = previous.startup_proof
acquisition = previous.acquisition
prerequisites = previous.prerequisites
runtime = previous.runtime
STOP = previous.STOP

if __name__ == "__main__":
    raise SystemExit(main())
