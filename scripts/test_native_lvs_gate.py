# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run native gate controls. Optionally check both external SRAM receipts."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "sw/tests/fixtures/native_lvs"


def check(path, digest, top, counts, accept):
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
            raise ValueError(f"Changed test input: {path}")
    result = subprocess.run(
        ["make", "check-native-lvs", f"LVS_DB={path}", f"LVS_TOP={top}"],
        cwd=ROOT, capture_output=True, text=True,
    )
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
    if len(rows) != 1 or rows[0]["circuit_pair_counts"] != counts or (result.returncode == 0) != accept:
        raise RuntimeError(result.stdout + result.stderr)
    print(path.name, top, "accepted" if accept else "rejected", counts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sram-dir", type=Path)
    args = parser.parse_args()
    good = "9026631788d724ba9e538451b34905953baa49dba7d7a16ea33920155ef02307"
    check(FIXTURES / "inv.lvsdb", good, "sg13g2_inv_1", {"Match": 1}, True)
    check(FIXTURES / "inv.lvsdb", good, "missing_top", {"Match": 1}, False)
    check(FIXTURES / "invfault.lvsdb", "7bdc2681fc0dd227d35811082f0f14b4cf9b595fdc481b385c97261aa801bc73",
          "sg13g2_inv_1", {"NoMatch": 1}, False)
    if args.sram_dir:
        check(args.sram_dir.resolve() / "sram256.lvsdb",
              "62ca8a802bf7aba893d76fd1e43bf310937fd00e277d72b6ffa61ac976b49735",
              "RM_IHPSG13_2P_256x16_c2_bm_bist", {"Match": 24, "Mismatch": 4, "NoMatch": 3, "Skipped": 1}, False)
        check(args.sram_dir.resolve() / "sram2048long.lvsdb",
              "c8a61ed8e7619399aeb4c36265a16ad20cb0d2ec997b89ede5180af335a80e40",
              "RM_IHPSG13_1P_2048x64_c2_bm_bist", {"Match": 23, "Mismatch": 5, "NoMatch": 2, "Skipped": 1}, False)
