#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Save and verify a physical connectivity database without repeating extraction.

Checkpoint integrity and probe equivalence are not chip/LVS acceptance. The
caller supplies registered physical layers, probe windows and pinned inputs.
"""

import json
from pathlib import Path

from check_chip_supply_connectivity import sha
from probe_supply_components import probe_window


def snapshot(db, extractor, probes, top):
    """Canonicalize equivalence classes; raw cluster numbers may be renumbered."""
    rows = []
    classes = {}
    for spec in probes:
        layer = extractor.layer_by_name(spec["layer"])
        if layer is None:
            raise ValueError("Checkpoint missing registered layer " + spec["layer"])
        result = probe_window(
            db,
            extractor,
            layer,
            db.Box(*spec["box_dbu"]),
            extractor.internal_layout().dbu,
            top,
        )
        samples = []
        for sample in sorted(result["samples"], key=lambda s: s["point_um"]):
            key = (sample["circuit"], sample["cluster"])
            # Retain missing/unresolved status; canonical IDs never authorize
            # cross-instance joins when the circuit is child-local.
            if key not in classes:
                classes[key] = len(classes)
            samples.append(
                dict(
                    point_um=sample["point_um"],
                    circuit=key[0],
                    equivalence_class=classes[key],
                )
            )
        rows.append(
            dict(
                probe=spec,
                status=result["status"],
                errors=result["errors"],
                samples=samples,
            )
        )
    return rows


def save(db, extractor, output, probes, top, input_sha256):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    if not extractor.include_floating_subcircuits:
        raise ValueError("Enable include_floating_subcircuits before extraction")
    if not probes or not input_sha256:
        raise ValueError("Explicit probes and source hashes required")
    for path, digest in input_sha256.items():
        if sha(Path(path)) != digest:
            raise ValueError("Checkpoint input hash mismatch")
    before = snapshot(db, extractor, probes, top)
    database = output / "connectivity.l2n.gz"
    extractor.write(str(database))
    with database.open("rb") as source:
        if source.read(2) != b"\x1f\x8b":
            raise ValueError("Expected compressed native connectivity database")
    restored = db.LayoutToNetlist()
    restored.read(str(database))
    if (
        list(extractor.layer_names()) != list(restored.layer_names())
        or extractor.internal_layout().dbu != restored.internal_layout().dbu
        or before != snapshot(db, restored, probes, top)
    ):
        raise ValueError(
            "Connectivity checkpoint changed registered layers or probe equivalence"
        )
    for path, digest in input_sha256.items():
        if sha(Path(path)) != digest:
            raise ValueError("Input changed during checkpoint serialization")
    manifest = dict(
        status="PASS_CHECKPOINT_ROUNDTRIP_ONLY",
        floating_subcircuits_retained=True,
        database=database.name,
        database_bytes=database.stat().st_size,
        database_sha256=sha(database),
        input_sha256=input_sha256,
        method_sha256=sha(Path(__file__)),
        probe_method_sha256=sha(Path(__file__).with_name("probe_supply_components.py")),
        klayout_version=db.__version__,
        layers=list(extractor.layer_names()),
        dbu=extractor.internal_layout().dbu,
        top=top,
        probes=probes,
        probe_snapshot=before,
        chip_connectivity_accepted=False,
        full_chip_lvs_accepted=False,
        manufacturing_approval=False,
    )
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def load(db, directory, expected_manifest_sha256):
    """Require an independently pinned manifest before reading a database."""
    directory = Path(directory)
    manifest_path = directory / "manifest.json"
    if sha(manifest_path) != expected_manifest_sha256:
        raise ValueError("Checkpoint manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text())
    if manifest["status"] != "PASS_CHECKPOINT_ROUNDTRIP_ONLY":
        raise ValueError("Unverified checkpoint")
    if manifest["database"] != "connectivity.l2n.gz":
        raise ValueError("Unexpected checkpoint database name")
    if (
        manifest["method_sha256"] != sha(Path(__file__))
        or manifest["probe_method_sha256"]
        != sha(Path(__file__).with_name("probe_supply_components.py"))
        or manifest["klayout_version"] != db.__version__
    ):
        raise ValueError("Checkpoint method or tool version differs")
    database = directory / manifest["database"]
    if (
        database.stat().st_size != manifest["database_bytes"]
        or sha(database) != manifest["database_sha256"]
    ):
        raise ValueError("Checkpoint database hash/size mismatch")
    restored = db.LayoutToNetlist()
    restored.read(str(database))
    if (
        list(restored.layer_names()) != manifest["layers"]
        or restored.internal_layout().dbu != manifest["dbu"]
        or snapshot(db, restored, manifest["probes"], manifest["top"])
        != manifest["probe_snapshot"]
    ):
        raise ValueError("Checkpoint replay differs")
    return restored, manifest
