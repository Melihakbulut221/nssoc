#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Losslessly select explicit columns, preserving every native transient timepoint."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

COLUMNS = ("time", "v(ip)", "v(inn)", "v(scp)", "v(scn)", "v(qp)", "v(qn)")


def project(source, output, expected_sha):
    source, output = Path(source), Path(output)
    if output.exists() or source.is_symlink():
        raise ValueError("Fresh output and regular source required")
    digest = hashlib.sha256()
    count = 0
    # Raw token equality matters: no conversion, interpolation or temporal thinning.
    with (
        gzip.open(source, "rb") as src,
        gzip.open(output, "wb", compresslevel=9) as dst,
    ):
        header = next(src)
        digest.update(header)
        names = header.decode("ascii").split()
        if len(names) != len(set(names)) or any(n not in names for n in COLUMNS):
            raise ValueError("Native columns are missing or duplicate")
        indices = [names.index(n) for n in COLUMNS]
        dst.write(("\t".join(COLUMNS) + "\n").encode("ascii"))
        for line in src:
            digest.update(line)
            tokens = line.split()
            if len(tokens) != len(names):
                raise ValueError("Native data row width differs")
            dst.write(b"\t".join(tokens[i] for i in indices) + b"\n")
            count += 1
    if digest.hexdigest() != expected_sha:
        output.unlink()
        raise ValueError("Original full waveform hash differs")
    # Independently reopen both files, compare every retained token and row count.
    with gzip.open(source, "rb") as src, gzip.open(output, "rb") as dst:
        next(src)
        if next(dst).decode("ascii").split() != list(COLUMNS):
            raise ValueError("Projected header differs")
        for line in src:
            if next(dst).split() != [line.split()[i] for i in indices]:
                raise ValueError("Projected token differs")
        if dst.read():
            raise ValueError("Extra projected rows")
    return dict(
        status="PASS_EXACT_NATIVE_COLUMN_PROJECTION",
        original_full_wave_sha256=expected_sha,
        projected_gzip_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
        projected_bytes=output.stat().st_size,
        original_columns=len(names),
        retained_columns=list(COLUMNS),
        original_column_indices=indices,
        rows=count,
        time_downsampled=False,
        every_selected_token_rechecked=True,
        full_waveform_retained=False,
        scope="Seven selected raw native columns at every original timepoint. This is not a complete native waveform or a replacement for full 19-HBT headroom/current remeasurement.",
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sha256", required=True)
    ap.add_argument("--receipt", type=Path, required=True)
    args = ap.parse_args()
    if args.receipt.exists():
        ap.error("Fresh receipt required")
    result = project(args.source, args.out, args.sha256)
    args.receipt.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
