#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Serialize first, exit the producer, then verify in a fresh Linux process.

A prepared checkpoint is never accepted by the existing consumer. This avoids
holding both the extracted and reloaded graphs in the serialization process.
"""

import argparse
import json
import os
from pathlib import Path

import supply_checkpoint
from check_chip_supply_connectivity import sha
from supply_checkpoint import snapshot


def identity(pid):
    stat = Path(f"/proc/{pid}/stat")
    try:
        fields = stat.read_text().rsplit(") ", 1)[1].split()
    except FileNotFoundError:
        return None
    return dict(
        pid=pid,
        birth=fields[19],
        boot_id=Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
    )


def check_sources(pins):
    if not pins:
        raise ValueError("Explicit source hashes required")
    for path, digest in pins.items():
        if sha(Path(path)) != digest:
            raise ValueError("Checkpoint input hash mismatch")


def prepare(db, extractor, output, probes, top, input_sha256, checkpoint_layers=None):
    """Write data and a PREPARED receipt only; caller must then exit."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    if not extractor.include_floating_subcircuits:
        raise ValueError("Enable include_floating_subcircuits before extraction")
    if not probes:
        raise ValueError("Explicit probes required")
    check_sources(input_sha256)
    available_layers = list(extractor.layer_names())
    layers = available_layers if checkpoint_layers is None else checkpoint_layers
    if (not layers or len(set(layers)) != len(layers)
            or not set(layers) <= set(available_layers)
            or not {p["layer"] for p in probes} <= set(layers)):
        raise ValueError("Checkpoint layer contract must include every probe layer")
    before = snapshot(db, extractor, probes, top)
    database = output / "connectivity.l2n.gz"
    extractor.write(str(database))
    with database.open("rb") as source:
        if source.read(2) != b"\x1f\x8b":
            raise ValueError("Expected compressed native connectivity database")
    check_sources(input_sha256)
    manifest = dict(
        status="PREPARED_NOT_VERIFIED",
        producer=identity(os.getpid()),
        staged_method_sha256=sha(Path(__file__)),
        floating_subcircuits_retained=True,
        database=database.name,
        database_bytes=database.stat().st_size,
        database_sha256=sha(database),
        input_sha256=input_sha256,
        method_sha256=sha(Path(supply_checkpoint.__file__)),
        probe_method_sha256=sha(Path(__file__).with_name("probe_supply_components.py")),
        klayout_version=db.__version__,
        layers=layers,
        excluded_preparation_layers=[name for name in available_layers if name not in layers],
        dbu=extractor.internal_layout().dbu,
        top=top,
        probes=probes,
        probe_snapshot=before,
        chip_connectivity_accepted=False,
        full_chip_lvs_accepted=False,
        manufacturing_approval=False,
    )
    (output / "prepared.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def verify(db, directory, expected_prepared_sha256):
    """Promote only after the producer exits and native replay agrees."""
    directory = Path(directory)
    final_path = directory / "manifest.json"
    if final_path.exists():
        raise FileExistsError("Final checkpoint already exists")
    prepared_path = directory / "prepared.json"
    if sha(prepared_path) != expected_prepared_sha256:
        raise ValueError("Prepared manifest hash mismatch")
    manifest = json.loads(prepared_path.read_text())
    if manifest["status"] != "PREPARED_NOT_VERIFIED":
        raise ValueError("Unexpected prepared status")
    producer = manifest["producer"]
    if identity(producer["pid"]) == producer:
        raise ValueError("Producer must exit before checkpoint verification")
    if (
        manifest["staged_method_sha256"] != sha(Path(__file__))
        or manifest["method_sha256"] != sha(Path(supply_checkpoint.__file__))
        or manifest["probe_method_sha256"]
        != sha(Path(__file__).with_name("probe_supply_components.py"))
        or manifest["klayout_version"] != db.__version__
    ):
        raise ValueError("Checkpoint method or tool version differs")
    if not manifest["floating_subcircuits_retained"] or not manifest["probes"]:
        raise ValueError("Missing floating retention or probes")
    if manifest["database"] != "connectivity.l2n.gz":
        raise ValueError("Unexpected checkpoint database name")
    check_sources(manifest["input_sha256"])
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
    check_sources(manifest["input_sha256"])
    if sha(prepared_path) != expected_prepared_sha256:
        raise ValueError("Prepared manifest changed during verification")
    manifest.update(
        status="PASS_CHECKPOINT_ROUNDTRIP_ONLY",
        prepared_sha256=expected_prepared_sha256,
        verifier=identity(os.getpid()),
    )
    # Exclusive creation prevents replacement of an accepted checkpoint.
    with final_path.open("x") as target:
        target.write(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--prepared-sha256", required=True)
    args = parser.parse_args()
    import klayout.db as db

    result = verify(db, args.checkpoint, args.prepared_sha256)
    print(result["status"])


if __name__ == "__main__":
    main()
