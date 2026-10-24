#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Frozen1us acquisition with bounded transport publisher; unchanged physics.

V2's50.5816ns capture remains ERROR after an authenticated TLS handshake timeout.
Only the publisher implementation and explicit evidence pins change. All539
native devices, deck, time steps, acquisition windows,100ppm/50ps limits, lossless
part queue,50MiB capture ceiling and512MiB free floor remain inherited.
"""
import hashlib
from pathlib import Path

import characterize_pcie_pll_acquisition_v2 as previous
import publish_pcie_native_capture_v3 as publication

PREVIOUS_SHA = "e902a71626fef5ad0727f52123a7ee5ce2e6fe6b91aaf223130f68e029ed9531"
PUBLISHER_SHA = "b2ea742c31c20c19bf02b30b3b1954342d5aa73772732dc69c8f170f46e1fa0f"
RELEASE_TAG = previous.RELEASE_TAG
require = previous.require
life = previous.life
BRIDGES = {}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_parent():
    require(sha(previous.__file__) == PREVIOUS_SHA, "Frozen acquisitionV2")
    require(sha(publication.__file__) == PUBLISHER_SHA, "Frozen retry publisherV3")
    require(sha(publication.lifecycle.__file__) == publication.OWNER_SHA, "Frozen publisher group owner")
    return previous.verify_parent()


require(sha(previous.__file__) == PREVIOUS_SHA, "Exact inherited acquisitionV2")
require(sha(publication.__file__) == PUBLISHER_SHA, "Exact bounded retry publisher")
namespace = dict(previous.namespace)
namespace.update(__file__=__file__, __name__=__name__, __doc__=__doc__,
                 verify_parent=verify_parent, publication=publication)
publisher_namespace = dict(previous.publisher_namespace)
publisher_namespace.update(__file__=__file__, __name__=__name__, publication=publication,
                           PUBLISHER_SHA=PUBLISHER_SHA, RELEASE_TAG=RELEASE_TAG)


def bridge(source, replacements, name):
    original = source
    for old, new in replacements:
        require(source.count(old) == 1, "Unique publication-only bridge: " + name)
        source = source.replace(old, new)
    BRIDGES[name] = dict(original_sha256=hashlib.sha256(original.encode()).hexdigest(),
                        modified_sha256=hashlib.sha256(source.encode()).hexdigest(),
                        exact_replacements=replacements)
    return source


publisher_source = bridge(previous.publisher_source,
                          [("class OwnedPublisherV2:", "class OwnedPublisherV3:")], "publisher")
exec(compile(publisher_source, __file__ + ":publisher", "exec"), publisher_namespace)
OwnedPublisherV3 = publisher_namespace["OwnedPublisherV3"]
namespace["OwnedPublisherV3"] = OwnedPublisherV3
run_source = bridge(previous.run_source, [
    ("OwnedPublisherV2(owner)", "OwnedPublisherV3(owner)"),
    ('+ [__file__, str(reference)]',
     '+ [__file__, str(publication.__file__), str(publication.lifecycle.__file__), str(reference)]'),
], "run")
exec(compile(run_source, __file__ + ":run", "exec"), namespace)
run = namespace["run"]
main_source = previous.main_source
exec(compile(main_source, __file__ + ":main", "exec"), namespace)
main = namespace["main"]
stream_deck = previous.stream_deck
measurements = previous.measurements
startup_proof = previous.startup_proof
acquisition = previous.acquisition
prerequisites = previous.prerequisites
runtime = previous.runtime
STOP = previous.STOP

if __name__ == "__main__":
    raise SystemExit(main())
