#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prove boot range safety and require two broken predicates to be refuted."""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cbmc", default="cbmc")
    args = parser.parse_args()
    binary = shutil.which(args.cbmc)
    if binary is None:
        parser.error(f"CBMC not found: {args.cbmc}")
    binary = str(Path(binary).absolute())
    out = ROOT / "hw/soc/out/boot-geometry"
    out.mkdir(parents=True, exist_ok=True)
    harness = ROOT / "sw/formal/boot_geometry.c"
    header = ROOT / "hw/soc/tb/sw/boot_geometry.h"
    mutations = {
        "real": None,
        "odd_entry": "      && (entry & 1u) == 0u\n",
        "cross_slot": "      && bytes <= slot_bytes - header_bytes\n",
    }
    for name, remove in mutations.items():
        with tempfile.TemporaryDirectory(prefix="boot-geometry-") as temp:
            root = Path(temp)
            copy = root / harness.relative_to(ROOT)
            copy.parent.mkdir(parents=True)
            copy.write_bytes(harness.read_bytes())
            predicate = root / header.relative_to(ROOT)
            predicate.parent.mkdir(parents=True)
            text = header.read_text()
            if remove:
                if text.count(remove) != 1:
                    raise RuntimeError(f"{name}: mutation site is no longer unique")
                text = text.replace(remove, "")
            predicate.write_text(text)
            command = [binary, str(copy), "--function", "main", "--bounds-check",
                       "--pointer-check", "--unsigned-overflow-check", "--signed-overflow-check",
                       "--conversion-check", "--div-by-zero-check", "--unwinding-assertions"]
            result = subprocess.run(command, text=True, capture_output=True, timeout=60)
            (out / f"{name}.log").write_text(result.stdout + result.stderr)
            expected = 10 if remove else 0
            verdict = "VERIFICATION FAILED" if remove else "VERIFICATION SUCCESSFUL"
            if result.returncode != expected or verdict not in result.stdout:
                raise RuntimeError(f"{name}: unexpected exit {result.returncode}; see {out / (name + '.log')}")
            print(f"{name}: {verdict}" + (" (expected counterexample)" if remove else ""))


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        sys.exit(str(exc))
