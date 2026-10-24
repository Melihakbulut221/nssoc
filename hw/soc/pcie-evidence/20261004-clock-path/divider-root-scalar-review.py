# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import gzip, json, math, hashlib, statistics
from pathlib import Path

root = Path("/dev/shm/nssoc-div2-condition-native-final")
meta = json.loads((root / "result.json").read_text())
rows = []
for name in ["nominal", "cold_slow"]:
    p = root / name / "wave.dat.gz"
    case = next(r for r in meta["cases"] if r["case"]["name"] == name)
    want = case["outputs"]["wave.dat.gz"]
    want = want if isinstance(want, str) else want["sha256"]
    assert hashlib.file_digest(p.open("rb"), "sha256").hexdigest() == want
    t = []
    ci = []
    qo = []
    cm = []
    with gzip.open(p, "rt") as f:
        header = next(f).split()
        indices = [
            header.index(n) for n in ["time", "v(clkp)", "v(clkn)", "v(qp)", "v(qn)"]
        ]
        previous = -1.0
        n = 0
        first = None
        for line in f:
            fields = line.split()
            assert len(fields) == len(header)
            r = [float(fields[i]) for i in indices]
            assert all(math.isfinite(x) for x in r)
            assert r[0] > previous
            previous = r[0]
            first = r[0] if first is None else first
            n += 1
            if r[0] >= 4e-9:
                t.append(r[0])
                ci.append(r[1] - r[2])
                qo.append(r[3] - r[4])
                cm.append((r[3] + r[4]) / 2)
    assert first == 0 and previous >= 12e-9 and n > 1000

    def rising(v):
        return [
            t[i - 1] + (t[i] - t[i - 1]) * (-v[i - 1]) / (v[i] - v[i - 1])
            for i in range(1, len(t))
            if v[i - 1] <= 0 < v[i]
        ]

    a = rising(ci)
    b = rising(qo)
    assert len(a) > 30 and len(b) > 15
    count = [sum(x < z < y for z in a) for x, y in zip(b, b[1:])]
    assert count and set(count) == {2}
    fi = (len(a) - 1) / (a[-1] - a[0])
    fo = (len(b) - 1) / (b[-1] - b[0])
    assert abs(fi / (2 * fo) - 1) < 0.001
    rows.append(
        {
            "case": name,
            "wave_sha256": want,
            "complete_rows": n,
            "input_frequency_hz": fi,
            "output_frequency_hz": fo,
            "input_edges_per_output_period": sorted(set(count)),
            "output_diff_range_v": [min(qo), max(qo)],
            "output_common_mode_range_v": [min(cm), max(cm)],
        }
    )
r = {
    "status": "PASS_INDEPENDENT_TWO_WAVE_SCALAR_REVIEW",
    "scope": "Root independent standard-library parser/interpolated sign crossings, all serial edge counts and common-mode ranges for nominal and cold_slow. No native rerun, alternate device-physics model or full matrix peer review.",
    "measurement_window_s": [4e-9, 12e-9],
    "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "cases": rows,
}
Path(
    "hw/soc/pcie-evidence/20261004-clock-path/divider-root-scalar-review.json"
).write_text(json.dumps(r, indent=2) + "\n")
print(json.dumps(rows, indent=2))
