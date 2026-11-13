# SPDX-License-Identifier: Apache-2.0
"""Read-only connectivity diagnosis; collapsed wire R is NOT an electrical model."""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from cdr_netlist_neighbourhood import load

root, out = map(Path, sys.argv[1:])
model = root / "native/composition-n1/model.cir"
record = root / "derived/loaded-n1-nominal_late.json"
before = hashlib.sha256(model.read_bytes()).hexdigest()
devices = load(model)
rows = [dict(name=name, model=kind, wire_equivalence_nodes=nodes,
             parameters={t.split("=", 1)[0]: t.split("=", 1)[1]
                         for t in card.split() if "=" in t})
        for name, kind, nodes, card in devices]
counts = Counter(row["model"] for row in rows)
assert counts["npn13g2"] == 124, counts
assert len({row["name"] for row in rows}) == len(rows)
original = json.loads(record.read_text())
assert "groups" in original["binding"] and "aliases" in original["binding"]
assert hashlib.sha256(model.read_bytes()).hexdigest() == before
out.mkdir(parents=True, exist_ok=False)
report = dict(schema=1, source_run=41733225660,
    native_artifact_id=13283214752, model_sha256=before,
    record_sha256=hashlib.sha256(record.read_bytes()).hexdigest(),
    scope="Topology only. Wire resistors collapsed solely to identify connectivity; no simulation, no parasitic removal from any circuit, no acceptance claim.",
    native_source_unchanged=True, primitive_counts=dict(counts), devices=rows,
    binding=original["binding"])
(out / "topology.json").write_text(json.dumps(report, indent=2)+"
")
print(json.dumps(dict(model_sha256=before, primitive_counts=dict(counts))))
