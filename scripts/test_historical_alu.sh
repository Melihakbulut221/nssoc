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
git sparse-checkout set '/scripts/' '/sw/tests/' '/hw/soc/pnr/*lock.json' '/hw/soc/tb/' '/hw/soc/flow/' '/.github/workflows/' '/docs/evidence/*json'
git checkout --quiet HEAD
git restore --source="$original" --worktree -- \
    .github/workflows/timing-alu-qualification.yml \
    .github/workflows/timing-alu-state-bit-benchmark.yml \
    .github/workflows/timing-alu-state-bits-complete.yml \
    .github/workflows/timing-alu-state-partitions.yml \
    .github/workflows/timing-alu-state-refinement.yml \
    hw/soc/flow/sim_logic_boot_gl.py
"$python" -m pytest -q sw/tests/test_alu_boot_trace.py sw/tests/test_alu_hard_bits.py \
    sw/tests/test_alu_remaining_bits.py sw/tests/test_alu_state_refinement.py \
    sw/tests/test_alu_state_bit_benchmark.py
