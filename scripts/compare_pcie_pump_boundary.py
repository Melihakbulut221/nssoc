# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare saved loaded and isolated pump traces; never infer PLL acceptance.

Every raw column is checked for finite values. Only common pump/boundary
columns are retained in memory. Global supply/clamp currents are deliberately
excluded: they measure different loads in the two circuits.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pin(path):
    with Path(path).open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"bytes": Path(path).stat().st_size, "sha256": digest}


def canonical(name):
    return name[2:-1] if name.startswith("i(@") and name.endswith(")") else name


def read_trace(directory, columns):
    directory = Path(directory)
    result_path = directory / "result.json"
    result_pin = pin(result_path)
    result = json.loads(result_path.read_text())
    names = result["columns"]
    rows, width = result["rows"], len(names)
    require(0 < rows <= 2_000_000 and 0 < width <= 4096, "trace size")
    require(len(set(names)) == width and names[0] == "time", "column identity")
    require(all(name in names for name in columns), "missing observation")
    for name, expected in result["outputs"].items():
        require(Path(name).name == name, "nonlocal output")
        require(pin(directory / name) == expected, "output digest: " + name)
    index = [names.index(name) for name in columns]
    raw_hash, payload_hash = hashlib.sha256(), hashlib.sha256()
    selected = np.empty((rows, len(index)), dtype=np.float64)
    raw_bytes = 0
    with gzip.open(directory / "wave.raw.gz", "rb") as stream:
        header = bytearray()
        while not header.endswith(b"Binary:\n"):
            line = stream.readline(65537)
            require(line and len(header) + len(line) <= 1048576, "raw header")
            header.extend(line)
        raw_hash.update(header)
        raw_bytes += len(header)
        text = header.decode("ascii")
        require(f"No. Variables: {width}\n" in text, "header width")
        require("Flags: real\n" in text, "nonreal trace")
        table = [line.split() for line in text.split("Variables:\n", 1)[1].split("Binary:\n", 1)[0].splitlines()]
        require(table == result["raw_table"], "header table")
        require([canonical(row[1]) for row in table] == names, "table names")
        require([row[0] for row in table] == list(map(str, range(width))), "table indices")
        previous = -float("inf")
        for first in range(0, rows, 1024):
            count = min(1024, rows - first)
            payload = stream.read(count * width * 8)
            require(len(payload) == count * width * 8, "truncated payload")
            raw_hash.update(payload)
            payload_hash.update(payload)
            raw_bytes += len(payload)
            block = np.frombuffer(payload, dtype="<f8").reshape(count, width)
            require(np.isfinite(block).all(), "nonfinite raw sample")
            require(block[0, 0] > previous and np.all(np.diff(block[:, 0]) > 0), "time order")
            previous = block[-1, 0]
            selected[first:first + count] = block[:, index]
        trailer = stream.read(64)
        require(trailer == str(rows).encode() and not stream.read(1), "row-count trailer")
        raw_hash.update(trailer)
        raw_bytes += len(trailer)
    require(raw_bytes == result["raw_bytes"], "raw byte count")
    require(raw_hash.hexdigest() == result["raw_sha256"], "raw digest")
    require(payload_hash.hexdigest() == result["payload_sha256"], "payload digest")
    require(pin(result_path) == result_pin, "changed result")
    return selected, {"result": result_pin, "wave": result["outputs"]["wave.raw.gz"], "rows": rows, "width": width, "native_status": result["status"]}


def compare(loaded, isolated, lo=4e-9, hi=34e-9):
    left = json.loads((Path(loaded) / "result.json").read_text())
    right = json.loads((Path(isolated) / "result.json").read_text())
    require(right["config"]["state"] == "idle", "isolated case must be idle")
    require(left["outputs"]["pll_pfd_charge_pump_hv_v1.spice"] == right["outputs"]["pll_pfd_charge_pump_hv_v1.spice"], "pump source mismatch")
    boundaries = ["v(avdd)", "v(dvdd)", "v(up)", "v(down)", "v(vctrl)"]
    internal = [name for name in right["columns"] if "xloop.xdet.xcp." in name or name in ("v(xloop.xrhi.dt)", "v(xloop.xrlo.dt)")]
    columns = ["time"] + boundaries + internal
    a, apin = read_trace(loaded, columns)
    b, bpin = read_trace(isolated, columns)
    require(a[0, 0] <= lo < hi <= a[-1, 0] and b[0, 0] <= lo < hi <= b[-1, 0], "window coverage")
    # Union grid retains every recorded extremum of both piecewise-linear traces.
    time = np.unique(np.r_[lo, a[(a[:, 0] > lo) & (a[:, 0] < hi), 0], b[(b[:, 0] > lo) & (b[:, 0] < hi), 0], hi])
    metrics = {}
    for index, name in enumerate(columns[1:], 1):
        av = np.interp(time, a[:, 0], a[:, index])
        bv = np.interp(time, b[:, 0], b[:, index])
        difference = av - bv
        weights = np.diff(time) / (hi - lo)
        mean = lambda values: float(np.sum(weights * (values[:-1] + values[1:]) / 2))
        metrics[name] = {"loaded_min": float(av.min()), "loaded_max": float(av.max()), "loaded_mean": mean(av), "isolated_mean": mean(bv), "mean_difference": mean(difference), "max_abs_difference": float(np.max(np.abs(difference)))}
    return {"status": "COMPLETE_SAVED_IDLE_BOUNDARY_COMPARISON_NOT_PLL_ACCEPTANCE", "loaded": apin, "isolated": bpin, "pump_source": left["outputs"]["pll_pfd_charge_pump_hv_v1.spice"], "window_s": [lo, hi], "union_samples": len(time), "boundary_columns": boundaries, "metrics": metrics, "global_supply_and_clamp_currents_compared": False, "new_native_simulation": False, "dynamic_pump_transfer_validated": False, "pll_lock_accepted": False, "serial_phy_complete": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("loaded", type=Path)
    parser.add_argument("isolated", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = compare(args.loaded, args.isolated)
    result["reader"] = pin(__file__)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"])


if __name__ == "__main__":
    main()
