#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Replay current ALU tests with the dependencies whose exact bytes they pin.
set -euo pipefail
root=$(git rev-parse --show-toplevel)
original=14f5b2f38ce6040433b888b3522800b1b264a04d
head=$(git -C "$root" rev-parse HEAD)
python=$(command -v "${PYTHON:-python3}")
if ! git -C "$root" cat-file -e "$original^{commit}"; then
    echo "Fetch the historical source with git fetch --depth=1 origin $original" >&2
    exit 1
fi
temp=$(mktemp -d)
work=$temp/replay
trap 'git -C "$root" worktree remove --force "$work" >/dev/null; rmdir "$temp"' EXIT
git -C "$root" worktree add --quiet --no-checkout --detach "$work" "$head"
cd "$work"
git sparse-checkout init --no-cone
git sparse-checkout set '/scripts/' '/sw/tests/' '/hw/soc/pnr/*lock.json' '/hw/soc/tb/' '/hw/soc/flow/' '/.github/workflows/' '/docs/evidence/*json' '/docs/evidence/alu-prefix-c10-input-20261002.tar.xz'
git checkout --quiet HEAD
git restore --source="$original" --worktree -- \
    .github/workflows/timing-alu-qualification.yml \
    .github/workflows/timing-alu-state-bit-benchmark.yml \
    .github/workflows/timing-alu-state-bits-complete.yml \
    .github/workflows/timing-alu-state-partitions.yml \
    .github/workflows/timing-alu-state-refinement.yml \
    hw/soc/flow/sim_logic_boot_gl.py
# The C10 protocol tests pin an 81-file capture including generated Ibex RTL.
# Restore the exact source view into this temporary worktree only.
"$python" - "$temp" <<'PYTHON'
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, "scripts")
import run_core_ack_protocol as core

root = Path.cwd()
lock = json.loads((root / core.LOCK).read_text())
evidence = json.loads((root / core.EVIDENCE).read_text())
archive = lock["archive"]
assert core.ack.sha(root / core.LOCK) == core.LOCK_SHA
assert core.ack.sha(root / core.EVIDENCE) == core.EVIDENCE_SHA
assert core.pin(root / archive["path"]) == {k: archive[k] for k in ("bytes", "sha256")}
pins = {name: lock["files"]["repo/" + name] for name in evidence["current_source_files_verified"]}
stage = Path(sys.argv[1]) / "captured"
core.restore_sources(stage, pins, root)
shutil.copytree(stage / "sources", root, dirs_exist_ok=True)
shutil.rmtree(stage)
core.source_contract(root)
PYTHON
"$python" -m pytest -q sw/tests/test_alu_boot_trace.py sw/tests/test_alu_hard_bits.py \
    sw/tests/test_alu_remaining_bits.py sw/tests/test_alu_state_refinement.py \
    sw/tests/test_alu_state_bit_benchmark.py sw/tests/test_core_ack_protocol.py
