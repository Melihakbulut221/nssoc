#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Repeat only selected exact sampler decks with the other pinned native ngspice."""

import argparse
import gzip
import json
from pathlib import Path
import shutil
import tempfile

import characterize_pcie_sampler_v2 as s
import review_pcie_sampler_v2 as review


def selection(baseline):
    pvt = [r for r in baseline["cases"] if r["case"]["name"].startswith("hbt_")]
    names = [
        "hbt_typ_res_typ_27_1.8",
        min(
            pvt,
            key=lambda r: (r["measurement"]["min_signed_margin_v"], r["case"]["name"]),
        )["case"]["name"],
        min(
            pvt,
            key=lambda r: (
                min(d["min_vce_v"] for d in r["measurement"]["devices"].values()),
                r["case"]["name"],
            ),
        )["case"]["name"],
        *[r["case"]["name"] for r in baseline["cases"] if r["case"]["fault"]],
    ]
    return list(dict.fromkeys(names))


def outcomes(rows):
    return all(
        "measurement" in r
        and r["measurement"]["screen_pass"] == (r["case"]["fault"] is None)
        for r in rows
    )


def native_run(directory, ngspice, output):
    directory, output = Path(directory).resolve(), Path(output).resolve()
    if output.exists() or not output.is_relative_to(Path("/dev/shm")):
        raise ValueError("Fresh /dev/shm output required")
    base_bytes = (directory / "result.json").read_bytes()
    baseline = json.loads(base_bytes)
    review.source_contract(baseline)
    sha = review.digest(ngspice)
    if sha not in s.RUNTIMES or s.RUNTIMES[sha] == baseline["runtime_version"]:
        raise ValueError("A different explicitly pinned simulator is required")
    osdi = Path(baseline["compile"]["command"][3])
    review.verify(osdi, baseline["osdi_sha256"])
    source_pins = dict(baseline["source_sha256"])
    source_pins.update(
        {
            str(p): review.digest(p)
            for p in (
                Path(__file__).resolve(),
                Path(review.__file__).resolve(),
                Path(ngspice).resolve(),
                osdi,
            )
        }
    )
    output.mkdir()
    (output / "baseline-result.json").write_bytes(base_bytes)
    record = dict(
        status="RUNNING",
        baseline_result_sha256=review.digest(output / "baseline-result.json"),
        source_sha256=source_pins,
        baseline_runtime=baseline["runtime_version"],
        runtime=s.RUNTIMES[sha],
        native_runtime=str(Path(ngspice).resolve()),
        selected_names=selection(baseline),
        cases=[],
        full_campaign_repeated=False,
        pcie_compliance=False,
        physical_qualification=False,
        manufacturing_approval=False,
    )

    def save():
        (output / "result.tmp").write_text(json.dumps(record, indent=2) + "\n")
        (output / "result.tmp").replace(output / "result.json")

    try:
        save()
        for name in record["selected_names"]:
            original = next(r for r in baseline["cases"] if r["case"]["name"] == name)
            dest = output / name
            dest.mkdir()
            for member in ("bench.cir", s.NETLIST.name, s.rx.NETLIST.name):
                review.verify(
                    directory / name / member, original["output_sha256"][member]
                )
                shutil.copyfile(directory / name / member, dest / member)
            row = dict(
                case=original["case"], baseline_measurement=original["measurement"]
            )
            record["cases"].append(row)
            save()
            try:
                row["execution"] = s.rx.execute(
                    [str(Path(ngspice).resolve()), "-n", "-b", "bench.cir"],
                    dest,
                    dest / "run.log",
                )
                row["measurement"] = s.measure(dest / "wave.dat", row["case"])
            except RuntimeError as exc:
                row["native_failure"] = str(exc)
                row["attempted_command"] = [
                    str(Path(ngspice).resolve()),
                    "-n",
                    "-b",
                    "bench.cir",
                ]
                # A failed native solve is preserved, never accepted as a
                # completed measurement-based negative control.
            row["numerical_diagnostics"] = s.diagnostics.diagnostics(
                (dest / "run.log").read_text()
            )
            if (dest / "wave.dat").exists():
                row["wave_sha256"] = review.digest(dest / "wave.dat")
                with (
                    (dest / "wave.dat").open("rb") as src,
                    gzip.open(dest / "wave.dat.gz", "wb", compresslevel=1) as dst,
                ):
                    shutil.copyfileobj(src, dst)
                (dest / "wave.dat").unlink()
            row["output_sha256"] = {p.name: review.digest(p) for p in dest.iterdir()}
            save()
            print(
                name,
                row.get("measurement", {}).get("screen_pass"),
                row.get("measurement", {}).get("min_signed_margin_v"),
                flush=True,
            )
        for path, expected in source_pins.items():
            review.verify(path, expected)
        record["source_bytes_unchanged"] = True
        record["all_expected_outcomes"] = outcomes(record["cases"])
        record["numerical_clean"] = all(
            r["numerical_diagnostics"]["numerical_clean"]
            for r in record["cases"]
            if not r["case"]["fault"]
        )
        record["status"] = (
            "FAIL_CROSS_VERSION_SAMPLER_SCREEN"
            if not record["all_expected_outcomes"]
            else "CROSS_VERSION_SCREEN_PASS_NUMERICAL_RESIDUAL"
            if not record["numerical_clean"]
            else "PASS_CROSS_VERSION_LIMITED_SAMPLER_SCREEN"
        )
    except BaseException as exc:
        record.update(status="ERROR_PRESERVED", error=repr(exc))
        raise
    finally:
        save()
    return record


def replay(directory):
    root = Path(directory).resolve()
    result_sha = review.digest(root / "result.json")
    record = json.loads((root / "result.json").read_text())
    review.verify(root / "baseline-result.json", record["baseline_result_sha256"])
    baseline = json.loads((root / "baseline-result.json").read_text())
    models, osdi = review.source_contract(baseline)
    if record["source_bytes_unchanged"] is not True or record[
        "selected_names"
    ] != selection(baseline):
        raise ValueError("Native selection differs")
    if record["full_campaign_repeated"] is not False or any(
        record[k] is not False
        for k in ("pcie_compliance", "physical_qualification", "manufacturing_approval")
    ):
        raise ValueError("Subset was relabelled as complete qualification")
    ng = Path(record["native_runtime"])
    sha = review.digest(ng)
    if (
        sha not in s.RUNTIMES
        or s.RUNTIMES[sha] != record["runtime"]
        or record["runtime"] == baseline["runtime_version"]
    ):
        raise ValueError("Cross-version runtime differs")
    expected = dict(baseline["source_sha256"])
    expected.update(
        {
            str(p): review.digest(p)
            for p in (
                Path(__file__).resolve(),
                Path(review.__file__).resolve(),
                ng,
                osdi,
            )
        }
    )
    if record["source_sha256"] != expected:
        raise ValueError("Complete cross-version source closure differs")
    for p, sha in expected.items():
        review.verify(p, sha)
    if [r["case"]["name"] for r in record["cases"]] != record["selected_names"]:
        raise ValueError("Missing or duplicate native selection")
    with tempfile.TemporaryDirectory(
        prefix="sampler-cross-review-", dir="/dev/shm"
    ) as scratch:
        for row in record["cases"]:
            case = row["case"]
            original = next(
                r for r in baseline["cases"] if r["case"]["name"] == case["name"]
            )
            if (
                case != original["case"]
                or row["baseline_measurement"] != original["measurement"]
            ):
                raise ValueError("Baseline case changed")
            folder = root / case["name"]
            expected_names = {
                "bench.cir",
                "run.log",
                s.NETLIST.name,
                s.rx.NETLIST.name,
            }
            if "wave_sha256" in row:
                expected_names.add("wave.dat.gz")
            if (
                set(row["output_sha256"]) != expected_names
                or {p.name for p in folder.iterdir()} != expected_names
            ):
                raise ValueError("Cross-version output inventory differs")
            for n, sha in row["output_sha256"].items():
                review.verify(folder / n, sha)
            if (folder / "bench.cir").read_text() != s.deck(case, models, osdi) or (
                folder / s.NETLIST.name
            ).read_text() != s.circuit(case):
                raise ValueError("Cross-version changed actual native deck/circuit")
            review.verify(folder / s.rx.NETLIST.name, s.RX_PIN)
            command = [str(ng), "-n", "-b", "bench.cir"]
            if "native_failure" in row:
                raw_log = (folder / "run.log").read_text().lower()
                if (
                    "measurement" in row
                    or row.get("attempted_command") != command
                    or not any(
                        marker in raw_log
                        for marker in ("error", "aborted", "timestep too small")
                    )
                ):
                    raise ValueError("Unproven native failure was relabelled")
            elif (
                row["execution"]["returncode"] != 0
                or row["execution"]["command"] != command
            ):
                raise ValueError("Cross-version native execution differs")
            if "wave_sha256" in row:
                wave = Path(scratch) / "wave.dat"
                s.diagnostics.unpack_wave(
                    folder / "wave.dat.gz", wave, row["wave_sha256"]
                )
                if (
                    "native_failure" not in row
                    and s.measure(wave, case) != row["measurement"]
                ):
                    raise ValueError("Cross-version raw waveform differs")
                wave.unlink()
            if (
                s.diagnostics.diagnostics((folder / "run.log").read_text())
                != row["numerical_diagnostics"]
            ):
                raise ValueError("Cross-version numerical warnings changed")
    if outcomes(record["cases"]) is not record["all_expected_outcomes"]:
        raise ValueError("Cross-version expected outcomes changed")
    clean = all(
        r["numerical_diagnostics"]["numerical_clean"]
        for r in record["cases"]
        if not r["case"]["fault"]
    )
    status = (
        "FAIL_CROSS_VERSION_SAMPLER_SCREEN"
        if not record["all_expected_outcomes"]
        else "CROSS_VERSION_SCREEN_PASS_NUMERICAL_RESIDUAL"
        if not clean
        else "PASS_CROSS_VERSION_LIMITED_SAMPLER_SCREEN"
    )
    if record["status"] != status or record["numerical_clean"] is not clean:
        raise ValueError("Cross-version result was relabelled")
    for p, sha in expected.items():
        review.verify(p, sha)
    review.verify(root / "result.json", result_sha)
    return dict(
        status="PASS_NATIVE_CROSS_VERSION_CAPTURE_REVIEW_ONLY",
        producer_status=status,
        result_sha256=result_sha,
        waveform_count=sum("wave_sha256" in r for r in record["cases"]),
        fully_remeasured_waveform_count=sum(
            "measurement" in r for r in record["cases"]
        ),
        native_failed_case_names=[
            r["case"]["name"] for r in record["cases"] if "native_failure" in r
        ],
        selected_names=record["selected_names"],
        source_sha256=expected,
        all_expected_outcomes=record["all_expected_outcomes"],
        numerical_clean=clean,
        no_spice_execution=True,
        full_campaign_repeated=False,
        pcie_compliance=False,
        physical_qualification=False,
        manufacturing_approval=False,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--directory", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--ngspice", type=Path)
    ap.add_argument("--review", action="store_true")
    args = ap.parse_args()
    if args.out.exists():
        ap.error("Fresh output required")
    if args.review:
        result = replay(args.directory)
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    else:
        if not args.ngspice:
            ap.error("--ngspice required for native run")
        result = native_run(args.directory, args.ngspice.resolve(), args.out)
    print(result["status"])
    return exit_code(result["status"])


def exit_code(status):
    if status in (
        "PASS_NATIVE_CROSS_VERSION_CAPTURE_REVIEW_ONLY",
        "PASS_CROSS_VERSION_LIMITED_SAMPLER_SCREEN",
    ):
        return 0
    if status == "CROSS_VERSION_SCREEN_PASS_NUMERICAL_RESIDUAL":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
