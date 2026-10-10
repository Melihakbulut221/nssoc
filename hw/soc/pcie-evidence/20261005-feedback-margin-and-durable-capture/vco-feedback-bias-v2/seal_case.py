# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import gzip
import hashlib
import json
import sys
import tarfile

import numpy as np

R = Path.cwd()
B = Path(__file__).resolve().parent
sys.path.insert(0, str(R / "scripts"))
import characterize_pcie_vco_v6_feedback_bias_v2 as candidate
m = candidate.core
PARENT = B.parent / "pcie-vco-v6-feedback-v1-20261005"


def pin(path):
    path = Path(path)
    with path.open("rb") as f:
        return dict(bytes=path.stat().st_size, sha256=hashlib.file_digest(f, "sha256").hexdigest())


frozen = dict(json.loads((PARENT / "source-freeze-observer-v2.json").read_text()),
              **json.loads((B.parent / "pcie-vco-v6-feedback-bias-v1-20261005" / "source-freeze.json").read_text()),
              **json.loads((B / "source-freeze.json").read_text()))
assert len(frozen) == 19 and all(pin(R / name) == value for name, value in frozen.items())

name = sys.argv[1]
assert name in ("06-01", "085-01", "disconnect-01", "modulus-01")
P = Path("/dev/shm/nssoc-vco-v6-feedback-bias-v2-" + name)
r = json.loads((P / "result.json").read_text())
assert r["status"] in ("PASS_NATIVE_LOADED_FEEDBACK_SCREEN", "FAIL_NATIVE_LOADED_FEEDBACK_SCREEN")
assert all(pin(p) == h for p, h in r["inputs"].items())
assert all(pin(P / p) == h for p, h in r["outputs"].items())
with gzip.open(P / "wave.raw.gz", "rb") as f:
    header, meta = m.life.tiny.parse_header(f, m.n.vectors(r["devices"], r["config"]["extra_vectors"]))
    body = f.read()
width = len(meta["columns"]) * 8
assert body[r["rows"] * width:] == str(r["rows"]).encode()
payload = body[:r["rows"] * width]
assert hashlib.sha256(header + body).hexdigest() == r["raw_sha256"]
assert hashlib.sha256(payload).hexdigest() == r["payload_sha256"]
assert len(header) + len(body) == r["raw_bytes"]
data = dict(zip(m.stream.previous.data_names(meta["columns"]), np.frombuffer(payload, "<f8").reshape(r["rows"], -1).T))
assert all(np.isfinite(x).all() for x in data.values())
contacts = [x for x in r["devices"] if x["model"] in ("ptap1", "ntap1")]
other = [x for x in r["devices"] if x not in contacts]
safety = m.n.safety(data, other, r["config"]["window_s"])
assert safety["all_device_bounds"] == r["safety"]["all_device_bounds"][:424]
assert safety["model_geometry_range_issues"] == []
for row, reported in zip(contacts, r["safety"]["all_device_bounds"][424:]):
    volts = [data[f"v({x})"] if x != "0" else np.zeros(r["rows"]) for x in row["nets"]]
    actual = float(abs(volts[0] - volts[1]).max())
    assert reported["path"] == row["path"]
    assert reported["max_capture_terminal_difference"] == actual
    assert reported["inferred_ohmic_peak_a"] == actual / float(row["params"]["r"])
assert m.n.validate_time_grid(data["time"], 34e-9, 5e-12) == r["time_grid"]
assert m.measurement(data, r["config"]) == r["measurement"]
native = m.stream.previous.startup_proof(P, r)
assert all(r[k] == v for k, v in native.items())
# Additional descriptive amplitude diagnostic, not an after-the-fact changed gate.
t = data["time"]
diff = data["v(clkp)"] - data["v(clkn)"]
edges = [e for e in m.n.common.crossings(t, diff, 0) if 4e-9 <= e < 34e-9]
cycles = []
for a, b in zip(edges[:-1], edges[1:]):
    s = diff[(t >= a) & (t <= b)]
    cycles.append(dict(start_s=a, end_s=b, minimum_v=float(s.min()), maximum_v=float(s.max())))
review = dict(status="PASS_COMPLETE_RAW_REPLAY", native_result=pin(P / "result.json"),
    columns=len(meta["columns"]), rows=r["rows"], values=r["values"],
    all437_device_screens_reproduced=True, all_counts_measurements_reproduced=True,
    full_raw_sha256=r["raw_sha256"], descriptive_clock_cycles=cycles,
    descriptive_all_complete_cycles_signed300mV=all(x["minimum_v"] <= -.3 and x["maximum_v"] >= .3 for x in cycles),
    status_not_upgraded=True, no_native_rerun=True)
(B / f"review-{name}.json").write_text(json.dumps(review, indent=2) + "\n")
files = {}
for root in [P, m.HYBRID, Path("/dev/shm/nssoc-vco-v4-mim-v6-local-v1-wire-geometry-01"), Path("/dev/shm/nssoc-vco-v4-mim-v6-local-v1-wire-rc-01")]:
    for path in root.rglob("*"):
        if path.is_file():
            files["native/" + root.name + "/" + str(path.relative_to(root))] = path
for path in [Path(x) for x in m.stream.previous.method_inventory()] + [R / x for x in dict(json.loads((PARENT / "source-freeze-observer-v2.json").read_text()), **json.loads((B.parent / "pcie-vco-v6-feedback-bias-v1-20261005" / "source-freeze.json").read_text()), **json.loads((B / "source-freeze.json").read_text()))]:
    files["project/" + str(path.relative_to(R))] = path
for path in [B / "source-freeze.json", B / "source-controls01.log", B / "source-only-peer.json", B / "predeclared-campaign.json", B / f"review-{name}.json", B / "seal_case.py", B / f"native-{name}.log"]:
    if path.is_file():
        files["review/" + path.name] = path
for license_name in ("Apache-2.0", "CERN-OHL-W-2.0", "CC-BY-4.0"):
    files["licenses/" + license_name + ".txt"] = R / "LICENSES" / (license_name + ".txt")
notices = B / "NOTICES.txt"
if not notices.exists():
    notices.write_text("Copyright2026 Hasan Melih Akbulut. Project Python Apache-2.0; circuit CERN-OHL-W-2.0; native evidence CC-BY-4.0. Exact IHP PDK model/runtime pins are recorded; no upstream model implementations, OSDI or native binary redistributed. Full local VCO wire RC, explicit external BODY_SUBSTRATE and WIRE_CREF ideal boundaries; divider feedback schematic devices only. Only two physical first-stage pull-ups L6.4 to4um; all437 observations and screens retained. Finite27C34ns5ps, no closed PLL, PVT, jitter or product acceptance. All failed actual controls remain visible.\n")
files["review/NOTICES.txt"] = notices
members = {name: pin(path) for name, path in files.items()}
cap = B / ("pcie-vco-v6-loaded-feedback-bias-v2-" + name + ".tar.xz")
assert not cap.exists()
with tarfile.open(cap, "w:xz", preset=1, dereference=True) as arc:
    for member, path in files.items():
        arc.add(path, arcname=member, recursive=False)
seen = {}
with tarfile.open(cap, "r|xz") as arc:
    for entry in arc:
        assert entry.isfile()
        seen[entry.name] = dict(bytes=entry.size, sha256=hashlib.file_digest(arc.extractfile(entry), "sha256").hexdigest())
assert members == seen
assert all(pin(R / name) == value for name, value in frozen.items())
(B / f"members-{name}.json").write_text(json.dumps(members, indent=2) + "\n")
receipt = dict(status="SEALED_ALL_NATIVE_VALUES_FINITE_SCREEN", archive=dict(path=str(cap), **pin(cap)),
               members=len(members), member_inventory=pin(B / f"members-{name}.json"),
               native_result=pin(P / "result.json"), native_status=r["status"], replay=pin(B / f"review-{name}.json"))
(B / f"validation-{name}.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
