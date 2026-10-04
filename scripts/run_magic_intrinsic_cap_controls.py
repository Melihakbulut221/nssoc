#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Tiny native format-consumer controls, separate from actual writer reproduction."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

from check_magic_intrinsic_cap_retirement import close, require, spice

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
from check_pcie_rx_cell import execute  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def case_text(name):
    scale = 2 if name == "reader_scale2" else 1
    header = f"version 8.3\ntech ihp-sg13g2\nstyle ngspice()\nscale 1000 {scale} 0.5\n"
    substrate = 'substrate "sub!" 0 0 -100 -100 space 0 0\n'
    if name == "no_replacement":
        return (
            header + 'port "A" 1 0 0 0 4 m7\nnode "A" 0 100 0 0 m7 0 0\n' + substrate,
            None,
            100.0,
            False,
        )
    if name == "renamed_killnode":
        ext = (
            header
            + 'port "A" 1 0 0 0 4 m7\nport "B" 2 20 0 20 4 m7\nnode "OLD" 0 100 0 0 m7 0 0\nnode "A" 0 0 0 0 m7 0 0\nnode "B" 0 0 20 0 m7 0 0\n'
            + substrate
        )
        replacement = f'scale 1000 {scale} 0.5\nkillnode "OLD"\n'
    else:
        ext = (
            header
            + 'port "A" 1 0 0 0 4 m7\nport "B" 2 20 0 20 4 m7\nnode "B" 0 100 20 0 m7 0 0\nequiv "B" "A"\n'
            + substrate
        )
        adjustment = {
            "omitted_retirement": "",
            "wrong_retirement": 'subcap "B" -50\n',
            "duplicate_retirement": 'subcap "B" -100\nsubcap "B" -100\n',
        }.get(name, 'subcap "B" -100\n')
        replacement = f"scale 1000 {scale} 0.5\n" + adjustment
    replacement += (
        'rnode "B" 0 40 20 0 0\nrnode "A" 0 30 0 0 0\nrnode "A" 0 30 0 0 0\n'
        if name == "repeated_rnode"
        else 'rnode "B" 0 40 20 0 0\nrnode "A" 0 60 0 0 0\n'
    )
    replacement += 'resist "A" "B" 0.05\n'
    return (
        ext,
        replacement,
        100.0 * scale,
        name in {"omitted_retirement", "wrong_retirement", "duplicate_retirement"},
    )


def run(runtime, tech, out):
    require(not out.exists(), "Fresh native-control directory required")
    out.mkdir(parents=True)
    runtime, tech = runtime.resolve(), tech.resolve()
    inputs = {
        str(p): sha(p)
        for p in [
            Path(__file__),
            ROOT / "scripts/check_magic_intrinsic_cap_retirement.py",
            ROOT / "hw/soc/flow/check_pcie_rx_cell.py",
            *[p for p in runtime.rglob("*") if p.is_file()],
            *[p for p in tech.rglob("*") if p.is_file()],
        ]
    }
    result = {
        "status": "RUNNING",
        "scope": "Synthetic native extflat consumer semantics; not geometry/producer scaling qualification",
        "inputs": inputs,
        "cases": [],
    }
    for name in (
        "retained_name",
        "renamed_killnode",
        "repeated_rnode",
        "no_replacement",
        "reader_scale2",
        "omitted_retirement",
        "wrong_retirement",
        "duplicate_retirement",
    ):
        directory = out / name
        directory.mkdir()
        original, replacement, expected, negative = case_text(name)
        (directory / "tiny.ext").write_text(original)
        if replacement is not None:
            (directory / "tiny.res.ext").write_text(replacement)
        script = directory / "run.tcl"
        script.write_text(
            'puts "NSSOC_LOADED_NATIVE_LIBRARIES [info loaded]"\n'
            + f"cd {{{directory}}}\n"
            + "ext2spice lvs\next2spice global off\next2spice cthresh 0\next2spice rthresh 0\n"
            + "ext2spice extresist "
            + ("on" if replacement else "off")
            + "\next2spice -o tiny.spice tiny.ext\nquit -noprompt\n"
        )
        execution = execute(
            [
                "/usr/bin/env",
                "CAD_ROOT=" + str(runtime),
                "/usr/bin/tclsh8.6",
                runtime / "magic/tcl/magic.tcl",
                "-dnull",
                "-noconsole",
                "-rcfile",
                tech / "ihp-sg13g2.magicrc",
                script,
            ],
            directory,
            "native",
        )
        require(execution["returncode"] == 0, "Native format control failed")
        log = (directory / "native.log").read_text()
        require(
            str(runtime / "magic/tcl/tclmagic.so") in log, "Wrong native shared library"
        )
        netlist = spice(directory / "tiny.spice", inspect_negative_control=negative)
        require(
            netlist["ports"] == (["A"] if replacement is None else ["A", "B"]),
            "Native format control port identity",
        )
        require(
            netlist["resistors"] == ([] if replacement is None else [("A", "B", 0.05)]),
            "Native format control resistance identity",
        )
        require(
            all(b == "sub" for _, b, _ in netlist["capacitors"]),
            "Unexpected coupling in format control",
        )
        actual = sum(v * 1e18 for _, _, v in netlist["capacitors"])
        matched = close(actual, expected)
        require(
            matched != negative, "Native conservation control failed to discriminate"
        )
        result["cases"].append(
            dict(
                name=name,
                expected_af=expected,
                actual_af=actual,
                conservation_pass=matched,
                deliberate_negative=negative,
                native_execution=execution,
                netlist=netlist,
            )
        )
    require(all(sha(p) == h for p, h in inputs.items()), "Control input mutation")
    result.update(
        status="PASS_FIVE_NATIVE_CONSUMER_CONTROLS_THREE_REAL_NEGATIVE_EXPORTS",
        qualified_pex=False,
        supported_producer_cscale=1,
        outputs={
            str(p.relative_to(out)): sha(p) for p in out.rglob("*") if p.is_file()
        },
    )
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("runtime", "tech", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(run(args.runtime, args.tech, args.out)["status"])


if __name__ == "__main__":
    main()
